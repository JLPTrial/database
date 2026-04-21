#!/usr/bin/env python3

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cria o banco SQLite de um nível.")
    parser.add_argument("--schema", required=True, help="Caminho do schema SQL")
    parser.add_argument("--db", required=True, help="Caminho do .db de saída")
    parser.add_argument("--data-dir", required=True, help="Pasta de dados do nível")
    return parser.parse_args()


def validate_inputs(schema_path: Path, data_dir: Path) -> None:
    if not schema_path.is_file():
        raise FileNotFoundError(f"Schema não encontrado: {schema_path}")
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Pasta de dados não encontrada: {data_dir}")


def create_database(schema_path: Path, db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = schema_path.read_text(encoding="utf-8")

    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()


def _is_question_payload(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    return "question_text" in obj and "alternatives" in obj


def _collect_questions(node: Any) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []

    if _is_question_payload(node):
        collected.append(node)
        return collected

    if isinstance(node, list):
        for item in node:
            collected.extend(_collect_questions(item))
        return collected

    if isinstance(node, dict):
        for value in node.values():
            collected.extend(_collect_questions(value))

    return collected


def load_questions_from_json(data_dir: Path) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for json_file in sorted(data_dir.glob("*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        file_questions = _collect_questions(data)
        if not file_questions:
            raise ValueError(f"Nenhuma questão encontrada em: {json_file}")
        questions.extend(file_questions)

    if not questions:
        raise ValueError(f"Nenhuma questão encontrada na pasta: {data_dir}")

    return questions


def _upsert_statement(conn: sqlite3.Connection, question_command: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO statement (question_command) VALUES (?)",
        (question_command,),
    )
    cursor = conn.execute(
        "SELECT id FROM statement WHERE question_command = ?",
        (question_command,),
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Falha ao obter id de statement")
    return int(row[0])


def _insert_alternatives(conn: sqlite3.Connection, alternatives: dict[str, Any]) -> int:
    cursor = conn.execute(
        """
        INSERT INTO alternatives (
            alternative_1,
            alternative_2,
            alternative_3,
            alternative_4,
            correct_alternative
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            alternatives.get("alternative_1"),
            alternatives.get("alternative_2"),
            alternatives.get("alternative_3"),
            alternatives.get("alternative_4"),
            alternatives.get("correct_alternative"),
        ),
    )
    return int(cursor.lastrowid)


def _insert_media(conn: sqlite3.Connection, media: Any) -> int | None:
    if not media:
        return None
    if not isinstance(media, dict):
        raise ValueError("Campo 'media' deve ser objeto JSON ou null")

    contextual_text = media.get("contextual_text")
    if contextual_text is None:
        # Compatibilidade com chave legada já existente nos JSONs.
        contextual_text = media.get("text_content")

    contextual_text_id = None
    if contextual_text:
        contextual_text_id = _upsert_contextual_text(conn, str(contextual_text))

    cursor = conn.execute(
        """
        INSERT INTO media (contextual_text_id, image_file_path, audio_file_path)
        VALUES (?, ?, ?)
        """,
        (
            contextual_text_id,
            media.get("image_file_path"),
            media.get("audio_file_path"),
        ),
    )
    return int(cursor.lastrowid)


def _upsert_contextual_text(conn: sqlite3.Connection, contextual_text: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO contextual_texts (contextual_text) VALUES (?)",
        (contextual_text,),
    )
    cursor = conn.execute(
        "SELECT id FROM contextual_texts WHERE contextual_text = ?",
        (contextual_text,),
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Falha ao obter id de contextual_text")
    return int(row[0])


def _upsert_tag(conn: sqlite3.Connection, tag_name: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO tags (name) VALUES (?)",
        (tag_name,),
    )
    cursor = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Falha ao obter id da tag: {tag_name}")
    return int(row[0])


def seed_database(db_path: Path, questions: list[dict[str, Any]]) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")

        for question in questions:
            statement = question.get("statement") or {}
            question_command = statement.get("question_command")
            if not question_command:
                raise ValueError("Questão sem statement.question_command")

            alternatives = question.get("alternatives")
            if not isinstance(alternatives, dict):
                raise ValueError("Questão sem alternatives válido")

            question_type = question.get("question_type")
            question_text = question.get("question_text")
            if not question_type or not question_text:
                raise ValueError("Questão sem question_type ou question_text")

            statement_id = _upsert_statement(conn, question_command)
            alternative_id = _insert_alternatives(conn, alternatives)
            media_id = _insert_media(conn, question.get("media"))

            cursor = conn.execute(
                """
                INSERT INTO questions (
                    alternative_id,
                    media_id,
                    statement_id,
                    question_text,
                    question_type
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    alternative_id,
                    media_id,
                    statement_id,
                    question_text,
                    question_type,
                ),
            )
            question_id = int(cursor.lastrowid)

            tags = question.get("tags")
            if isinstance(tags, list):
                for tag in tags:
                    if not tag:
                        continue
                    tag_id = _upsert_tag(conn, str(tag).strip())
                    conn.execute(
                        "INSERT OR IGNORE INTO question_tags (question_id, tag_id) VALUES (?, ?)",
                        (question_id, tag_id),
                    )

        conn.commit()
    finally:
        conn.close()


def main() -> None:
    args = parse_args()

    schema_path = Path(args.schema)
    db_path = Path(args.db)
    data_dir = Path(args.data_dir)

    validate_inputs(schema_path, data_dir)
    create_database(schema_path, db_path)
    questions = load_questions_from_json(data_dir)
    seed_database(db_path, questions)


if __name__ == "__main__":
    main()

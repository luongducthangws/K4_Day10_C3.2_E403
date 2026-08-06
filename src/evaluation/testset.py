from __future__ import annotations

from typing import Any

import pandas as pd


from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    if df.empty:
        raise ValueError("Cannot build test set from an empty DataFrame.")

    sample_df = df.head(10)
    test_set: list[dict[str, Any]] = []

    for index, row in sample_df.iterrows():
        p_id = str(row["paper_id"])
        title = str(row["title"])

        # 1. Summary question
        test_set.append(
            {
                "id": f"q_{index}_summary",
                "question_type": "summary",
                "question": f"What is the main topic of the paper '{title}'?",
                "ground_truth": first_sentence(str(row["summary"])),
                "ground_truth_doc_ids": [p_id],
            }
        )

        # 2. Authors question
        test_set.append(
            {
                "id": f"q_{index}_authors",
                "question_type": "authors",
                "question": f"Who authored the paper '{title}'?",
                "ground_truth": str(row["authors_joined"]),
                "ground_truth_doc_ids": [p_id],
            }
        )

        # 3. Date question
        test_set.append(
            {
                "id": f"q_{index}_date",
                "question_type": "date",
                "question": f"When was the paper '{title}' published?",
                "ground_truth": str(row["published"]),
                "ground_truth_doc_ids": [p_id],
            }
        )

        # 4. Categories question
        test_set.append(
            {
                "id": f"q_{index}_categories",
                "question_type": "categories",
                "question": f"What categories does the paper '{title}' belong to?",
                "ground_truth": str(row["categories_joined"]),
                "ground_truth_doc_ids": [p_id],
            }
        )

    if output_path:
        write_json(output_path, test_set)

    return test_set

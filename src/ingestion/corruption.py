from __future__ import annotations

import pandas as pd


from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    corrupted_df = df.copy()
    logs = []

    if len(corrupted_df) < 5:
        return corrupted_df

    # 1. Drop latest 2 records
    dropped_ids = corrupted_df.iloc[:2]["paper_id"].tolist()
    corrupted_df = corrupted_df.iloc[2:].reset_index(drop=True)
    logs.append({"type": "drop_records", "count": len(dropped_ids), "paper_ids": dropped_ids})

    # 2. Blank summary on 2 rows
    blank_indices = [0, 2] if len(corrupted_df) > 2 else [0]
    for idx in blank_indices:
        p_id = corrupted_df.at[idx, "paper_id"]
        corrupted_df.at[idx, "summary"] = ""
        corrupted_df.at[idx, "summary_chars"] = 0
        logs.append({"type": "blank_summary", "paper_id": p_id})

    # 3. Add noise into summary on 2 rows
    noise_indices = [1, 3] if len(corrupted_df) > 3 else [1]
    for idx in noise_indices:
        p_id = corrupted_df.at[idx, "paper_id"]
        original = corrupted_df.at[idx, "summary"]
        corrupted_df.at[idx, "summary"] = "CORRUPTED NOISE: " + original[::2]
        logs.append({"type": "inject_noise", "paper_id": p_id})

    # 4. Truncate title on 2 rows
    trunc_indices = [4, 5] if len(corrupted_df) > 5 else [0]
    for idx in trunc_indices:
        p_id = corrupted_df.at[idx, "paper_id"]
        corrupted_df.at[idx, "title"] = corrupted_df.at[idx, "title"][:10] + "..."
        logs.append({"type": "truncate_title", "paper_id": p_id})

    # 5. Stale publication date on 2 rows
    stale_indices = [0, 1]
    for idx in stale_indices:
        p_id = corrupted_df.at[idx, "paper_id"]
        corrupted_df.at[idx, "published"] = "2010-01-01"
        corrupted_df.at[idx, "age_days"] = corrupted_df.at[idx, "age_days"] + 5000
        logs.append({"type": "stale_date", "paper_id": p_id})

    # 6. Add duplicate rows for 2 records
    dup_rows = corrupted_df.iloc[:2].copy()
    corrupted_df = pd.concat([corrupted_df, dup_rows], ignore_index=True)
    logs.append({"type": "add_duplicates", "count": len(dup_rows)})

    # 7. Rebuild text_for_embedding
    texts = []
    for _, row in corrupted_df.iterrows():
        texts.append(
            f"Title: {row['title']}\n"
            f"Authors: {row['authors_joined']}\n"
            f"Categories: {row['categories_joined']}\n"
            f"Published: {row['published']}\n"
            f"Summary: {row['summary']}"
        )
    corrupted_df["text_for_embedding"] = texts

    # 8. Write log
    if output_log_path:
        write_json(output_log_path, logs)

    return corrupted_df

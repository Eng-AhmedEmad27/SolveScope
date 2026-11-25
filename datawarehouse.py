import sqlite3
import pandas as pd

df = pd.read_csv("ecpc_problems_warehouse_master.csv")
conn = sqlite3.connect("ecpc_warehouse.db")
cur = conn.cursor()

cur.executescript("""
CREATE TABLE IF NOT EXISTS dim_contest (
    contest_id INTEGER PRIMARY KEY AUTOINCREMENT,
    contest TEXT UNIQUE,
    contest_year INTEGER
);

CREATE TABLE IF NOT EXISTS dim_topic (
    topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS fact_problems (
    problem_id INTEGER PRIMARY KEY,
    contest_id INTEGER REFERENCES dim_contest(contest_id),
    problem_letter TEXT,
    title TEXT,
    final_rating REAL,
    difficulty_tier TEXT,
    rating_source TEXT,
    hard_to_easy_rank INTEGER,
    easy_to_hard_rank INTEGER,
    primary_topic TEXT,
    topics_list TEXT,
    topics_source TEXT,
    time_limit_sec REAL,
    memory_limit_mb REAL,
    sections_statement TEXT,
    sections_input TEXT,
    sections_output TEXT
);

CREATE TABLE IF NOT EXISTS bridge_problem_topic (
    problem_id INTEGER REFERENCES fact_problems(problem_id),
    topic_id INTEGER REFERENCES dim_topic(topic_id),
    PRIMARY KEY (problem_id, topic_id)
);

CREATE INDEX IF NOT EXISTS idx_rating ON fact_problems(final_rating);
CREATE INDEX IF NOT EXISTS idx_title ON fact_problems(title);
""")

# 1. تحميل المسابقات والتصنيفات
for _, r in df[["contest", "contest_year"]].drop_duplicates().iterrows():
  cur.execute(
      "INSERT OR IGNORE INTO dim_contest (contest, contest_year) VALUES (?,"
      " ?)",
      (r["contest"], int(r["contest_year"])),
  )

all_topics = {
    t.strip()
    for s in df["topics_list"].dropna()
    for t in str(s).split(",")
    if t.strip()
}
for t in sorted(all_topics):
  cur.execute("INSERT OR IGNORE INTO dim_topic (topic_name) VALUES (?)", (t,))

contest_map = dict(
    cur.execute("SELECT contest, contest_id FROM dim_contest").fetchall()
)
topic_map = dict(
    cur.execute("SELECT topic_name, topic_id FROM dim_topic").fetchall()
)

# 2. تحميل المسائل وربطها بالتصنيفات
for _, r in df.iterrows():
  cur.execute(
      """
        INSERT OR REPLACE INTO fact_problems VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """,
      (
          int(r["problem_id"]),
          contest_map[r["contest"]],
          r["problem_letter"],
          r["title"],
          float(r["final_rating"]),
          r["difficulty_tier"],
          r["rating_source"],
          int(r["hard_to_easy_rank"]),
          int(r["easy_to_hard_rank"]),
          r["primary_topic"],
          r["topics_list"],
          r["topics_source"],
          None if pd.isna(r["time_limit_sec"]) else float(r["time_limit_sec"]),
          None if pd.isna(r["memory_limit_mb"]) else float(r["memory_limit_mb"]),
          r["sections_statement"],
          r["sections_input"],
          r["sections_output"],
      ),
  )
  for t in [x.strip() for x in str(r["topics_list"]).split(",") if x.strip()]:
    cur.execute(
        "INSERT OR IGNORE INTO bridge_problem_topic VALUES (?, ?)",
        (int(r["problem_id"]), topic_map[t]),
    )

conn.commit()
conn.close()
print("Done!")
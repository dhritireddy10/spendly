from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    created_at = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    return {
        "name": row["name"],
        "email": row["email"],
        "member_since": created_at.strftime("%B %Y"),
    }


def get_summary_stats(user_id):
    conn = get_db()

    total_row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
        "FROM expenses WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    top_category_row = conn.execute(
        "SELECT category, SUM(amount) AS category_total "
        "FROM expenses WHERE user_id = ? "
        "GROUP BY category "
        "ORDER BY category_total DESC "
        "LIMIT 1",
        (user_id,),
    ).fetchone()

    conn.close()

    transaction_count = total_row["count"]
    if transaction_count == 0:
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    return {
        "total_spent": total_row["total"],
        "transaction_count": transaction_count,
        "top_category": top_category_row["category"],
    }


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT date, description, category, amount
        FROM expenses
        WHERE user_id = ?
        ORDER BY date DESC, created_at DESC, id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_category_breakdown(user_id):
    conn = get_db()
    rows = conn.execute(
        """
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE user_id = ?
        GROUP BY category
        ORDER BY total DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()

    if not rows:
        return []

    grand_total = sum(row["total"] for row in rows)
    if grand_total == 0:
        return []

    breakdown = [
        {"name": row["category"], "amount": row["total"]}
        for row in rows
    ]

    pct_values = [round((item["amount"] / grand_total) * 100) for item in breakdown]
    remainder = 100 - sum(pct_values)
    if remainder != 0:
        largest_index = max(range(len(breakdown)), key=lambda i: breakdown[i]["amount"])
        pct_values[largest_index] += remainder

    for item, pct in zip(breakdown, pct_values):
        item["pct"] = pct

    return breakdown

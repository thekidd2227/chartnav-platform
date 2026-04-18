import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "chartnav.db"


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO organizations (name, slug)
        SELECT ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM organizations WHERE slug = ?
        )
        """,
        ("Demo Eye Clinic", "demo-eye-clinic", "demo-eye-clinic"),
    )

    cur.execute("SELECT id FROM organizations WHERE slug = ?", ("demo-eye-clinic",))
    org_id = cur.fetchone()[0]

    cur.execute(
        """
        INSERT INTO locations (organization_id, name)
        SELECT ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM locations WHERE organization_id = ? AND name = ?
        )
        """,
        (org_id, "Main Clinic", org_id, "Main Clinic"),
    )

    cur.execute(
        """
        INSERT INTO users (organization_id, email, full_name, role)
        SELECT ?, ?, ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM users WHERE email = ?
        )
        """,
        (org_id, "admin@chartnav.local", "ChartNav Admin", "admin", "admin@chartnav.local"),
    )

    conn.commit()

    print("Seed complete.")
    print(f"organization_id={org_id}")

    rows = cur.execute(
        """
        SELECT o.name, l.name, u.email
        FROM organizations o
        LEFT JOIN locations l ON l.organization_id = o.id
        LEFT JOIN users u ON u.organization_id = o.id
        WHERE o.slug = ?
        """,
        ("demo-eye-clinic",),
    ).fetchall()

    print(rows)
    conn.close()


if __name__ == "__main__":
    main()

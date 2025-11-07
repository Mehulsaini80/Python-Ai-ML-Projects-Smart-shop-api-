import mysql.connector
from app import DB_CONFIG
from werkzeug.security import generate_password_hash


def main():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id, email, password FROM users WHERE password NOT LIKE '%:%'")
    rows = cursor.fetchall()

    if not rows:
        print("No plaintext passwords found. Nothing to update.")
        return

    print("The following users have plaintext passwords and will be hashed:")
    for r in rows:
        print(f"- id={r['id']}  email={r['email']}  password={r['password']}")

    confirm = input('Proceed to hash these passwords and update database? (yes/no): ').strip().lower()
    if confirm != 'yes':
        print('Aborted by user. No changes made.')
        return

    for r in rows:
        new_hash = generate_password_hash(r['password'])
        cursor.execute("UPDATE users SET password = %s WHERE id = %s", (new_hash, r['id']))
        print(f"Updated id={r['id']} email={r['email']}")

    conn.commit()
    cursor.close()
    conn.close()
    print('Done. All plaintext passwords were hashed.')


if __name__ == '__main__':
    main() 

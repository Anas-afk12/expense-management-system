from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import mysql.connector  # type: ignore
    from mysql.connector import Error as MySQLError  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    mysql = None
    MySQLError = Exception


BASE_DIR = Path(__file__).resolve().parent
SQLITE_DB_PATH = BASE_DIR / "group_expense_demo.db"
DEFAULT_MYSQL_DB = "group_expense_db"


@dataclass
class DatabaseConfig:
    backend: str
    host: str = "localhost"
    user: str = "root"
    password: str = ""
    database: str = DEFAULT_MYSQL_DB
    sqlite_path: Path = SQLITE_DB_PATH
    reset_sqlite: bool = False


class DatabaseClient:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.backend = "sqlite"
        self.conn = None

    @property
    def placeholder(self) -> str:
        return "%s" if self.backend == "mysql" else "?"

    def connect(self) -> None:
        if self.config.backend == "mysql" and mysql is not None:
            try:
                self._connect_mysql()
                self.backend = "mysql"
                print("Connected to MySQL successfully.")
                return
            except Exception as exc:
                print(f"MySQL connection failed, using local SQLite demo database instead: {exc}")

        self._connect_sqlite()
        self.backend = "sqlite"
        print(f"Using local SQLite database at: {self.config.sqlite_path}")

    def _connect_mysql(self) -> None:
        setup_conn = mysql.connector.connect(  # type: ignore[attr-defined]
            host=self.config.host,
            user=self.config.user,
            password=self.config.password,
        )
        try:
            setup_cur = setup_conn.cursor()
            setup_cur.execute(f"CREATE DATABASE IF NOT EXISTS {self._safe_identifier(self.config.database)}")
            setup_cur.close()
        finally:
            setup_conn.close()

        self.conn = mysql.connector.connect(  # type: ignore[attr-defined]
            host=self.config.host,
            user=self.config.user,
            password=self.config.password,
            database=self.config.database,
        )
        self._create_tables_mysql()

    def _connect_sqlite(self) -> None:
        if self.config.reset_sqlite and self.config.sqlite_path.exists():
            self.config.sqlite_path.unlink()
        self.conn = sqlite3.connect(self.config.sqlite_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables_sqlite()

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def reset_sqlite_database(self) -> None:
        if self.backend != "sqlite":
            raise RuntimeError("Reset is only available in SQLite demo mode.")
        self.close()
        if self.config.sqlite_path.exists():
            self.config.sqlite_path.unlink()
        self._connect_sqlite()

    def commit(self) -> None:
        if self.conn is not None:
            self.conn.commit()

    def rollback(self) -> None:
        if self.conn is not None:
            self.conn.rollback()

    def cursor(self, dictionary: bool = False):
        if self.conn is None:
            raise RuntimeError("Database is not connected")
        if self.backend == "mysql":
            if dictionary:
                return self.conn.cursor(dictionary=True)
            return self.conn.cursor()
        return self.conn.cursor()

    def execute(self, query: str, params: Sequence[object] = ()):
        cur = self.cursor()
        try:
            cur.execute(query, params)
            return cur
        except Exception:
            cur.close()
            raise

    def fetchall(self, query: str, params: Sequence[object] = (), dictionary: bool = False):
        cur = self.cursor(dictionary=dictionary)
        try:
            cur.execute(query, params)
            return cur.fetchall()
        finally:
            cur.close()

    def fetchone(self, query: str, params: Sequence[object] = (), dictionary: bool = False):
        cur = self.cursor(dictionary=dictionary)
        try:
            cur.execute(query, params)
            return cur.fetchone()
        finally:
            cur.close()

    def _safe_identifier(self, value: str) -> str:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value):
            raise ValueError("Invalid database identifier")
        return value

    def _create_tables_mysql(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS Users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS `Groups` (
                group_id INT AUTO_INCREMENT PRIMARY KEY,
                group_name VARCHAR(120) NOT NULL,
                created_by INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_groups_created_by
                    FOREIGN KEY (created_by) REFERENCES Users(user_id)
                    ON DELETE RESTRICT ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS GroupMembers (
                group_id INT NOT NULL,
                user_id INT NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, user_id),
                CONSTRAINT fk_group_members_group
                    FOREIGN KEY (group_id) REFERENCES `Groups`(group_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_group_members_user
                    FOREIGN KEY (user_id) REFERENCES Users(user_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS Expenses (
                expense_id INT AUTO_INCREMENT PRIMARY KEY,
                group_id INT NOT NULL,
                paid_by INT NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                description VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_expense_amount CHECK (amount > 0),
                CONSTRAINT fk_expenses_group
                    FOREIGN KEY (group_id) REFERENCES `Groups`(group_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_expenses_paid_by
                    FOREIGN KEY (paid_by) REFERENCES Users(user_id)
                    ON DELETE RESTRICT ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS ExpenseSplits (
                split_id INT AUTO_INCREMENT PRIMARY KEY,
                expense_id INT NOT NULL,
                user_id INT NOT NULL,
                amount_owed DECIMAL(10,2) NOT NULL,
                CONSTRAINT chk_split_amount CHECK (amount_owed >= 0),
                CONSTRAINT uk_expense_user UNIQUE (expense_id, user_id),
                CONSTRAINT fk_splits_expense
                    FOREIGN KEY (expense_id) REFERENCES Expenses(expense_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_splits_user
                    FOREIGN KEY (user_id) REFERENCES Users(user_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS Payments (
                payment_id INT AUTO_INCREMENT PRIMARY KEY,
                group_id INT NOT NULL,
                payer_id INT NOT NULL,
                payee_id INT NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                note VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_payment_amount CHECK (amount > 0),
                CONSTRAINT chk_payer_payee_different CHECK (payer_id <> payee_id),
                CONSTRAINT fk_payments_group
                    FOREIGN KEY (group_id) REFERENCES `Groups`(group_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_payments_payer
                    FOREIGN KEY (payer_id) REFERENCES Users(user_id)
                    ON DELETE RESTRICT ON UPDATE CASCADE,
                CONSTRAINT fk_payments_payee
                    FOREIGN KEY (payee_id) REFERENCES Users(user_id)
                    ON DELETE RESTRICT ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS DebtTransactions (
                transaction_id INT AUTO_INCREMENT PRIMARY KEY,
                group_id INT NOT NULL,
                debtor_id INT NOT NULL,
                creditor_id INT NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                source_type VARCHAR(20) NOT NULL,
                note VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT chk_debt_transaction_amount CHECK (amount > 0),
                CONSTRAINT fk_debt_transaction_group
                    FOREIGN KEY (group_id) REFERENCES `Groups`(group_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_debt_transaction_debtor
                    FOREIGN KEY (debtor_id) REFERENCES Users(user_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_debt_transaction_creditor
                    FOREIGN KEY (creditor_id) REFERENCES Users(user_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            """
            CREATE TABLE IF NOT EXISTS DebtLedger (
                ledger_id INT AUTO_INCREMENT PRIMARY KEY,
                group_id INT NOT NULL,
                debtor_id INT NOT NULL,
                creditor_id INT NOT NULL,
                amount DECIMAL(10,2) NOT NULL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CONSTRAINT chk_ledger_amount CHECK (amount >= 0),
                CONSTRAINT uk_ledger_pair UNIQUE (group_id, debtor_id, creditor_id),
                CONSTRAINT fk_ledger_group
                    FOREIGN KEY (group_id) REFERENCES `Groups`(group_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_ledger_debtor
                    FOREIGN KEY (debtor_id) REFERENCES Users(user_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CONSTRAINT fk_ledger_creditor
                    FOREIGN KEY (creditor_id) REFERENCES Users(user_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """,
            "CREATE INDEX idx_group_members_user ON GroupMembers(user_id)",
            "CREATE INDEX idx_expenses_group ON Expenses(group_id)",
            "CREATE INDEX idx_expenses_paid_by ON Expenses(paid_by)",
            "CREATE INDEX idx_splits_user ON ExpenseSplits(user_id)",
            "CREATE INDEX idx_payments_group ON Payments(group_id)",
            "CREATE INDEX idx_debt_transactions_group ON DebtTransactions(group_id)",
            "CREATE INDEX idx_debt_transactions_debtor ON DebtTransactions(debtor_id)",
            "CREATE INDEX idx_debt_transactions_creditor ON DebtTransactions(creditor_id)",
            "CREATE INDEX idx_ledger_group ON DebtLedger(group_id)",
            "CREATE INDEX idx_ledger_debtor ON DebtLedger(debtor_id)",
            "CREATE INDEX idx_ledger_creditor ON DebtLedger(creditor_id)",
        ]
        cur = self.cursor()
        try:
            for statement in statements:
                cur.execute(statement)
            self.commit()
        finally:
            cur.close()

    def _create_tables_sqlite(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS Users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS `Groups` (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES Users(user_id)
                    ON DELETE RESTRICT ON UPDATE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS GroupMembers (
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, user_id),
                FOREIGN KEY (group_id) REFERENCES `Groups`(group_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (user_id) REFERENCES Users(user_id)
                    ON DELETE CASCADE ON UPDATE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS Expenses (
                expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                paid_by INTEGER NOT NULL,
                amount NUMERIC NOT NULL,
                description TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES `Groups`(group_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (paid_by) REFERENCES Users(user_id)
                    ON DELETE RESTRICT ON UPDATE CASCADE,
                CHECK (amount > 0)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS ExpenseSplits (
                split_id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                amount_owed NUMERIC NOT NULL,
                UNIQUE (expense_id, user_id),
                FOREIGN KEY (expense_id) REFERENCES Expenses(expense_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (user_id) REFERENCES Users(user_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CHECK (amount_owed >= 0)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS Payments (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                payer_id INTEGER NOT NULL,
                payee_id INTEGER NOT NULL,
                amount NUMERIC NOT NULL,
                note TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES `Groups`(group_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (payer_id) REFERENCES Users(user_id)
                    ON DELETE RESTRICT ON UPDATE CASCADE,
                FOREIGN KEY (payee_id) REFERENCES Users(user_id)
                    ON DELETE RESTRICT ON UPDATE CASCADE,
                CHECK (amount > 0),
                CHECK (payer_id <> payee_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS DebtTransactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                debtor_id INTEGER NOT NULL,
                creditor_id INTEGER NOT NULL,
                amount NUMERIC NOT NULL,
                source_type TEXT NOT NULL,
                note TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES `Groups`(group_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (debtor_id) REFERENCES Users(user_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (creditor_id) REFERENCES Users(user_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CHECK (amount > 0)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS DebtLedger (
                ledger_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                debtor_id INTEGER NOT NULL,
                creditor_id INTEGER NOT NULL,
                amount NUMERIC NOT NULL DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (group_id, debtor_id, creditor_id),
                FOREIGN KEY (group_id) REFERENCES `Groups`(group_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (debtor_id) REFERENCES Users(user_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (creditor_id) REFERENCES Users(user_id)
                    ON DELETE CASCADE ON UPDATE CASCADE,
                CHECK (amount >= 0)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_group_members_user ON GroupMembers(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_expenses_group ON Expenses(group_id)",
            "CREATE INDEX IF NOT EXISTS idx_expenses_paid_by ON Expenses(paid_by)",
            "CREATE INDEX IF NOT EXISTS idx_splits_user ON ExpenseSplits(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_payments_group ON Payments(group_id)",
            "CREATE INDEX IF NOT EXISTS idx_debt_transactions_group ON DebtTransactions(group_id)",
            "CREATE INDEX IF NOT EXISTS idx_debt_transactions_debtor ON DebtTransactions(debtor_id)",
            "CREATE INDEX IF NOT EXISTS idx_debt_transactions_creditor ON DebtTransactions(creditor_id)",
            "CREATE INDEX IF NOT EXISTS idx_ledger_group ON DebtLedger(group_id)",
            "CREATE INDEX IF NOT EXISTS idx_ledger_debtor ON DebtLedger(debtor_id)",
            "CREATE INDEX IF NOT EXISTS idx_ledger_creditor ON DebtLedger(creditor_id)",
        ]
        cur = self.cursor()
        try:
            for statement in statements:
                cur.execute(statement)
            self.commit()
        finally:
            cur.close()


class GroupExpenseManager:
    def __init__(self, db: DatabaseClient):
        self.db = db

    def create_user(self) -> None:
        name = input("Enter user name: ").strip()
        email = input("Enter user email: ").strip().lower()
        if not name or not email:
            print("Name and email are required.")
            return
        try:
            cur = self.db.execute(
                f"INSERT INTO Users(name, email) VALUES ({self.db.placeholder}, {self.db.placeholder})",
                (name, email),
            )
            self.db.commit()
            print(f"User created with ID: {cur.lastrowid}")
        except Exception as exc:
            self.db.rollback()
            print(f"Could not create user: {exc}")

    def create_group(self) -> None:
        group_name = input("Enter group name: ").strip()
        created_by = self._read_int("Enter creator user ID: ")
        if created_by is None:
            return
        if not group_name:
            print("Group name cannot be empty.")
            return
        if not self._user_exists(created_by):
            print("Creator user does not exist.")
            return
        try:
            cur = self.db.execute(
                f"INSERT INTO `Groups`(group_name, created_by) VALUES ({self.db.placeholder}, {self.db.placeholder})",
                (group_name, created_by),
            )
            group_id = cur.lastrowid
            self.db.execute(
                f"INSERT INTO GroupMembers(group_id, user_id) VALUES ({self.db.placeholder}, {self.db.placeholder})",
                (group_id, created_by),
            )
            self.db.commit()
            print(f"Group created with ID: {group_id}")
            print("Creator automatically added as a member.")
        except Exception as exc:
            self.db.rollback()
            print(f"Could not create group: {exc}")

    def add_member_to_group(self) -> None:
        group_id = self._read_int("Enter group ID: ")
        user_id = self._read_int("Enter user ID to add: ")
        if group_id is None or user_id is None:
            return
        if not self._group_exists(group_id):
            print("Group does not exist.")
            return
        if not self._user_exists(user_id):
            print("User does not exist.")
            return
        try:
            self.db.execute(
                f"INSERT INTO GroupMembers(group_id, user_id) VALUES ({self.db.placeholder}, {self.db.placeholder})",
                (group_id, user_id),
            )
            self.db.commit()
            print("Member added to group.")
        except Exception as exc:
            self.db.rollback()
            print(f"Could not add member: {exc}")

    def view_group_members(self) -> None:
        group_id = self._read_int("Enter group ID: ")
        if group_id is None:
            return
        if not self._group_exists(group_id):
            print("Group does not exist.")
            return
        rows = self.db.fetchall(
            f"""
            SELECT u.user_id, u.name, u.email
            FROM GroupMembers gm
            JOIN Users u ON u.user_id = gm.user_id
            WHERE gm.group_id = {self.db.placeholder}
            ORDER BY u.user_id
            """,
            (group_id,),
            dictionary=True,
        )
        if not rows:
            print("No members in this group.")
            return
        print("Group Members:")
        for row in rows:
            print(f"- ID: {row['user_id']} | {row['name']} | {row['email']}")

    def add_expense(self) -> None:
        group_id = self._read_int("Enter group ID: ")
        paid_by = self._read_int("Enter payer user ID: ")
        amount = self._read_decimal("Enter amount: ")
        description = input("Enter description: ").strip()

        if None in (group_id, paid_by, amount):
            return
        if amount <= 0:
            print("Amount must be greater than zero.")
            return
        if not description:
            print("Description cannot be empty.")
            return

        members = self._get_group_member_ids(group_id)
        if not members:
            print("Group has no members. Add members first.")
            return
        if paid_by not in members:
            print("Payer must be a member of the group.")
            return

        split_amounts = self.calculate_splits(amount, members)
        try:
            cur = self.db.execute(
                f"""
                INSERT INTO Expenses(group_id, paid_by, amount, description)
                VALUES ({self.db.placeholder}, {self.db.placeholder}, {self.db.placeholder}, {self.db.placeholder})
                """,
                (group_id, paid_by, str(amount), description),
            )
            expense_id = cur.lastrowid
            for uid in members:
                self.db.execute(
                    f"""
                    INSERT INTO ExpenseSplits(expense_id, user_id, amount_owed)
                    VALUES ({self.db.placeholder}, {self.db.placeholder}, {self.db.placeholder})
                    """,
                    (expense_id, uid, str(split_amounts[uid])),
                )
                if uid != paid_by:
                    self._apply_ledger_change(group_id, uid, paid_by, split_amounts[uid])
            self.db.commit()
            print(f"Expense added with ID: {expense_id}")
            print("Expense split equally among all group members.")
            for uid in members:
                print(f"- User {uid}: {split_amounts[uid]:.2f}")
        except Exception as exc:
            self.db.rollback()
            print(f"Could not add expense: {exc}")

    def calculate_splits(self, total_amount: Decimal, member_ids: Sequence[int]) -> Dict[int, Decimal]:
        total_cents = int((total_amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        member_count = len(member_ids)
        base = total_cents // member_count
        remainder = total_cents % member_count
        result: Dict[int, Decimal] = {}
        for index, user_id in enumerate(sorted(member_ids)):
            cents = base + (1 if index < remainder else 0)
            result[user_id] = (Decimal(cents) / Decimal("100")).quantize(Decimal("0.01"))
        return result

    def record_payment(self) -> None:
        group_id = self._read_int("Enter group ID: ")
        payer_id = self._read_int("Enter payer user ID (who is paying now): ")
        payee_id = self._read_int("Enter payee user ID (who receives): ")
        amount = self._read_decimal("Enter payment amount: ")
        note = input("Enter note (optional): ").strip()

        if None in (group_id, payer_id, payee_id, amount):
            return
        if payer_id == payee_id:
            print("Payer and payee cannot be the same.")
            return
        if amount <= 0:
            print("Amount must be greater than zero.")
            return

        members = self._get_group_member_ids(group_id)
        if not members:
            print("Group does not exist or has no members.")
            return
        if payer_id not in members or payee_id not in members:
            print("Both payer and payee must be members of the group.")
            return

        try:
            self._apply_ledger_change(group_id, payer_id, payee_id, -amount)
            self.db.execute(
                f"""
                INSERT INTO Payments(group_id, payer_id, payee_id, amount, note)
                VALUES ({self.db.placeholder}, {self.db.placeholder}, {self.db.placeholder}, {self.db.placeholder}, {self.db.placeholder})
                """,
                (group_id, payer_id, payee_id, str(amount), note if note else None),
            )
            self.db.commit()
            print("Payment recorded successfully.")
            print(f"Ledger updated: {payer_id} -> {payee_id} by {amount:.2f}")
        except Exception as exc:
            self.db.rollback()
            print(f"Could not record payment: {exc}")

    def record_manual_debt(self) -> None:
        group_id = self._read_int("Enter group ID: ")
        debtor_id = self._read_int("Enter debtor user ID (who owes): ")
        creditor_id = self._read_int("Enter creditor user ID (who gets paid): ")
        amount = self._read_decimal("Enter debt amount: ")
        note = input("Enter note (optional): ").strip()

        if None in (group_id, debtor_id, creditor_id, amount):
            return
        if debtor_id == creditor_id:
            print("Debtor and creditor cannot be the same.")
            return
        if amount <= 0:
            print("Amount must be greater than zero.")
            return

        members = self._get_group_member_ids(group_id)
        if not members:
            print("Group does not exist or has no members.")
            return
        if debtor_id not in members or creditor_id not in members:
            print("Both debtor and creditor must be members of the group.")
            return

        try:
            self._apply_ledger_change(group_id, debtor_id, creditor_id, amount)
            self.db.execute(
                f"""
                INSERT INTO DebtTransactions(group_id, debtor_id, creditor_id, amount, source_type, note)
                VALUES ({self.db.placeholder}, {self.db.placeholder}, {self.db.placeholder}, {self.db.placeholder}, {self.db.placeholder}, {self.db.placeholder})
                """,
                (group_id, debtor_id, creditor_id, str(amount), "manual", note if note else None),
            )
            self.db.commit()
            print(f"Manual debt recorded: {debtor_id} owes {creditor_id} {amount:.2f}")
        except Exception as exc:
            self.db.rollback()
            print(f"Could not record manual debt: {exc}")

    def show_all_users(self) -> None:
        rows = self.db.fetchall(
            f"SELECT user_id, name, email, created_at FROM Users ORDER BY user_id",
            dictionary=True,
        )
        if not rows:
            print("No users found.")
            return
        print("All Users:")
        for row in rows:
            print(f"- ID: {row['user_id']} | {row['name']} | {row['email']} | {row['created_at']}")

    def show_all_groups(self) -> None:
        rows = self.db.fetchall(
            f"""
            SELECT g.group_id, g.group_name, g.created_by, u.name AS creator_name, g.created_at
            FROM `Groups` g
            JOIN Users u ON u.user_id = g.created_by
            ORDER BY g.group_id
            """,
            dictionary=True,
        )
        if not rows:
            print("No groups found.")
            return
        print("All Groups:")
        for row in rows:
            print(
                f"- ID: {row['group_id']} | {row['group_name']} | Created by: {row['creator_name']} (ID {row['created_by']}) | {row['created_at']}"
            )

    def show_debt_ledger(self) -> None:
        group_id = self._read_int("Enter group ID: ")
        if group_id is None:
            return
        if not self._group_exists(group_id):
            print("Group does not exist.")
            return
        rows = self.db.fetchall(
            f"""
            SELECT dl.debtor_id, debtor.name AS debtor_name,
                   dl.creditor_id, creditor.name AS creditor_name,
                   dl.amount
            FROM DebtLedger dl
            JOIN Users debtor ON debtor.user_id = dl.debtor_id
            JOIN Users creditor ON creditor.user_id = dl.creditor_id
            WHERE dl.group_id = {self.db.placeholder}
            ORDER BY debtor_name, creditor_name
            """,
            (group_id,),
            dictionary=True,
        )
        if not rows:
            print("No outstanding debts in this group.")
            return
        print("Debt Ledger:")
        for row in rows:
            print(f"- {row['debtor_name']} owes {row['creditor_name']}: {Decimal(str(row['amount'])):.2f}")

    def show_person_summary(self) -> None:
        user_id = self._read_int("Enter user ID: ")
        if user_id is None:
            return
        if not self._user_exists(user_id):
            print("User does not exist.")
            return

        user_row = self.db.fetchone(
            f"SELECT name, email FROM Users WHERE user_id = {self.db.placeholder}",
            (user_id,),
            dictionary=True,
        )
        if user_row is None:
            print("User does not exist.")
            return

        paid_row = self.db.fetchone(
            f"SELECT COALESCE(SUM(amount), 0) AS total_paid FROM Expenses WHERE paid_by = {self.db.placeholder}",
            (user_id,),
            dictionary=True,
        )
        owed_row = self.db.fetchone(
            f"SELECT COALESCE(SUM(amount_owed), 0) AS total_owed FROM ExpenseSplits WHERE user_id = {self.db.placeholder}",
            (user_id,),
            dictionary=True,
        )
        paid_total = Decimal(str(paid_row["total_paid"] or 0)).quantize(Decimal("0.01"))
        owed_total = Decimal(str(owed_row["total_owed"] or 0)).quantize(Decimal("0.01"))
        net_balance = (paid_total - owed_total).quantize(Decimal("0.01"))

        print(f"\nPerson Summary for {user_row['name']} ({user_row['email']})")
        print(f"- Total paid: {paid_total:.2f}")
        print(f"- Total owed: {owed_total:.2f}")
        print(f"- Net balance: {net_balance:.2f}")

        owes_rows = self.db.fetchall(
            f"""
            SELECT creditor.name AS creditor_name, dl.amount, g.group_name
            FROM DebtLedger dl
            JOIN Users creditor ON creditor.user_id = dl.creditor_id
            JOIN `Groups` g ON g.group_id = dl.group_id
            WHERE dl.debtor_id = {self.db.placeholder}
            ORDER BY g.group_name, creditor_name
            """,
            (user_id,),
            dictionary=True,
        )
        owed_by_rows = self.db.fetchall(
            f"""
            SELECT debtor.name AS debtor_name, dl.amount, g.group_name
            FROM DebtLedger dl
            JOIN Users debtor ON debtor.user_id = dl.debtor_id
            JOIN `Groups` g ON g.group_id = dl.group_id
            WHERE dl.creditor_id = {self.db.placeholder}
            ORDER BY g.group_name, debtor_name
            """,
            (user_id,),
            dictionary=True,
        )

        print("- Debts you owe:")
        if owes_rows:
            for row in owes_rows:
                print(f"  * {row['group_name']}: {row['creditor_name']} gets {Decimal(str(row['amount'])):.2f}")
        else:
            print("  * None")

        print("- Debts owed to you:")
        if owed_by_rows:
            for row in owed_by_rows:
                print(f"  * {row['group_name']}: {row['debtor_name']} owes {Decimal(str(row['amount'])):.2f}")
        else:
            print("  * None")

        expense_rows = self.db.fetchall(
            f"""
            SELECT e.expense_id, g.group_name, e.description, e.amount, e.created_at
            FROM Expenses e
            JOIN `Groups` g ON g.group_id = e.group_id
            WHERE e.paid_by = {self.db.placeholder}
            ORDER BY e.created_at DESC
            LIMIT 10
            """,
            (user_id,),
            dictionary=True,
        )

        print("- Recent expenses paid by this person:")
        if expense_rows:
            for row in expense_rows:
                print(
                    f"  * [{row['group_name']}] {row['description']} - {Decimal(str(row['amount'])):.2f} ({row['created_at']})"
                )
        else:
            print("  * None")

    def reset_demo_data(self) -> None:
        try:
            self.db.reset_sqlite_database()
            print("Demo database has been reset.")
        except Exception as exc:
            print(f"Could not reset demo database: {exc}")

    def view_balances(self) -> None:
        group_id = self._read_int("Enter group ID: ")
        if group_id is None:
            return
        members = self._get_group_member_ids(group_id)
        if not members:
            print("Group does not exist or has no members.")
            return

        rows = self.db.fetchall(
            f"""
            SELECT dl.debtor_id, debtor.name AS debtor_name,
                   dl.creditor_id, creditor.name AS creditor_name,
                   dl.amount
            FROM DebtLedger dl
            JOIN Users debtor ON debtor.user_id = dl.debtor_id
            JOIN Users creditor ON creditor.user_id = dl.creditor_id
            WHERE dl.group_id = {self.db.placeholder}
            ORDER BY debtor_name, creditor_name
            """,
            (group_id,),
            dictionary=True,
        )

        if not rows:
            print("All settled. No outstanding balances.")
            return

        print("Outstanding Balances:")
        for row in rows:
            print(f"- {row['debtor_name']} owes {row['creditor_name']}: {Decimal(str(row['amount'])):.2f}")

    def _apply_ledger_change(self, group_id: int, debtor_id: int, creditor_id: int, delta: Decimal) -> None:
        if debtor_id == creditor_id or delta == 0:
            return

        delta = delta.quantize(Decimal("0.01"))

        if delta > 0:
            reverse_row = self.db.fetchone(
                f"""
                SELECT amount
                FROM DebtLedger
                WHERE group_id = {self.db.placeholder}
                  AND debtor_id = {self.db.placeholder}
                  AND creditor_id = {self.db.placeholder}
                """,
                (group_id, creditor_id, debtor_id),
            )
            if reverse_row is not None:
                reverse_amount = Decimal(str(reverse_row[0])).quantize(Decimal("0.01"))
                if reverse_amount >= delta:
                    remaining = reverse_amount - delta
                    if remaining <= Decimal("0.00"):
                        self.db.execute(
                            f"""
                            DELETE FROM DebtLedger
                            WHERE group_id = {self.db.placeholder}
                              AND debtor_id = {self.db.placeholder}
                              AND creditor_id = {self.db.placeholder}
                            """,
                            (group_id, creditor_id, debtor_id),
                        )
                    else:
                        self.db.execute(
                            f"""
                            UPDATE DebtLedger
                            SET amount = {self.db.placeholder}
                            WHERE group_id = {self.db.placeholder}
                              AND debtor_id = {self.db.placeholder}
                              AND creditor_id = {self.db.placeholder}
                            """,
                            (str(remaining), group_id, creditor_id, debtor_id),
                        )
                    return
                delta = delta - reverse_amount
                self.db.execute(
                    f"""
                    DELETE FROM DebtLedger
                    WHERE group_id = {self.db.placeholder}
                      AND debtor_id = {self.db.placeholder}
                      AND creditor_id = {self.db.placeholder}
                    """,
                    (group_id, creditor_id, debtor_id),
                )

            forward_row = self.db.fetchone(
                f"""
                SELECT amount
                FROM DebtLedger
                WHERE group_id = {self.db.placeholder}
                  AND debtor_id = {self.db.placeholder}
                  AND creditor_id = {self.db.placeholder}
                """,
                (group_id, debtor_id, creditor_id),
            )
            if forward_row is None:
                self.db.execute(
                    f"""
                    INSERT INTO DebtLedger(group_id, debtor_id, creditor_id, amount)
                    VALUES ({self.db.placeholder}, {self.db.placeholder}, {self.db.placeholder}, {self.db.placeholder})
                    """,
                    (group_id, debtor_id, creditor_id, str(delta)),
                )
            else:
                new_amount = (Decimal(str(forward_row[0])) + delta).quantize(Decimal("0.01"))
                self.db.execute(
                    f"""
                    UPDATE DebtLedger
                    SET amount = {self.db.placeholder}
                    WHERE group_id = {self.db.placeholder}
                      AND debtor_id = {self.db.placeholder}
                      AND creditor_id = {self.db.placeholder}
                    """,
                    (str(new_amount), group_id, debtor_id, creditor_id),
                )
            return

        payment_amount = abs(delta)
        forward_row = self.db.fetchone(
            f"""
            SELECT amount
            FROM DebtLedger
            WHERE group_id = {self.db.placeholder}
              AND debtor_id = {self.db.placeholder}
              AND creditor_id = {self.db.placeholder}
            """,
            (group_id, debtor_id, creditor_id),
        )
        if forward_row is None:
            raise ValueError("No outstanding debt exists for this payment direction.")

        current_amount = Decimal(str(forward_row[0])).quantize(Decimal("0.01"))
        if payment_amount > current_amount:
            raise ValueError("Payment exceeds the outstanding debt.")

        remaining = current_amount - payment_amount
        if remaining <= Decimal("0.00"):
            self.db.execute(
                f"""
                DELETE FROM DebtLedger
                WHERE group_id = {self.db.placeholder}
                  AND debtor_id = {self.db.placeholder}
                  AND creditor_id = {self.db.placeholder}
                """,
                (group_id, debtor_id, creditor_id),
            )
        else:
            self.db.execute(
                f"""
                UPDATE DebtLedger
                SET amount = {self.db.placeholder}
                WHERE group_id = {self.db.placeholder}
                  AND debtor_id = {self.db.placeholder}
                  AND creditor_id = {self.db.placeholder}
                """,
                (str(remaining), group_id, debtor_id, creditor_id),
            )

    def _read_int(self, prompt: str) -> Optional[int]:
        raw = input(prompt).strip()
        if not raw:
            print("Input required.")
            return None
        try:
            value = int(raw)
            if value <= 0:
                print("Value must be a positive integer.")
                return None
            return value
        except ValueError:
            print("Invalid integer input.")
            return None

    def _read_decimal(self, prompt: str) -> Optional[Decimal]:
        raw = input(prompt).strip()
        if not raw:
            print("Input required.")
            return None
        try:
            return Decimal(raw).quantize(Decimal("0.01"))
        except Exception:
            print("Invalid decimal input.")
            return None

    def _user_exists(self, user_id: int) -> bool:
        row = self.db.fetchone(
            f"SELECT 1 FROM Users WHERE user_id = {self.db.placeholder}",
            (user_id,),
        )
        return row is not None

    def _group_exists(self, group_id: int) -> bool:
        row = self.db.fetchone(
            f"SELECT 1 FROM `Groups` WHERE group_id = {self.db.placeholder}",
            (group_id,),
        )
        return row is not None

    def _get_group_member_ids(self, group_id: int) -> List[int]:
        rows = self.db.fetchall(
            f"SELECT user_id FROM GroupMembers WHERE group_id = {self.db.placeholder} ORDER BY user_id",
            (group_id,),
        )
        return [int(row[0]) for row in rows]

    def _get_user_names(self, user_ids: Iterable[int]) -> Dict[int, str]:
        ids = list(user_ids)
        if not ids:
            return {}
        placeholders = ",".join([self.db.placeholder] * len(ids))
        rows = self.db.fetchall(
            f"SELECT user_id, name FROM Users WHERE user_id IN ({placeholders})",
            tuple(ids),
            dictionary=True,
        )
        return {int(row["user_id"]): str(row["name"]) for row in rows}


def print_menu() -> None:
    print("\n=== Group Expense Management System ===")
    print("1. Create User")
    print("2. Create Group")
    print("3. Add Member to Group")
    print("4. View Group Members")
    print("5. Add Expense")
    print("6. View Group Balances")
    print("7. Record Payment")
    print("8. Show All Users")
    print("9. Show All Groups")
    print("10. Reset Demo Data")
    print("11. View Debt Ledger")
    print("12. View Person Summary")
    print("13. Record Manual Debt")
    print("14. Exit")


def build_config() -> DatabaseConfig:
    print("Choose database mode:")
    print("1. MySQL")
    print("2. SQLite demo mode (works immediately on this machine)")
    choice = input("Enter choice [2]: ").strip() or "2"

    if choice == "1":
        host = input("MySQL host (default: localhost): ").strip() or "localhost"
        user = input("MySQL user (default: root): ").strip() or "root"
        password = input("MySQL password: ").strip()
        database = input(f"Database name (default: {DEFAULT_MYSQL_DB}): ").strip() or DEFAULT_MYSQL_DB
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", database):
            print("Invalid database name. Falling back to SQLite demo mode.")
            return DatabaseConfig(backend="sqlite", reset_sqlite=True)
        return DatabaseConfig(backend="mysql", host=host, user=user, password=password, database=database)

    return DatabaseConfig(backend="sqlite", reset_sqlite=True)


def main() -> None:
    config = build_config()
    db = DatabaseClient(config)
    try:
        db.connect()
    except Exception as exc:
        print(f"Could not start database: {exc}")
        return

    manager = GroupExpenseManager(db)

    try:
        while True:
            print_menu()
            choice = input("Enter your choice: ").strip()
            if choice == "1":
                manager.create_user()
            elif choice == "2":
                manager.create_group()
            elif choice == "3":
                manager.add_member_to_group()
            elif choice == "4":
                manager.view_group_members()
            elif choice == "5":
                manager.add_expense()
            elif choice == "6":
                manager.view_balances()
            elif choice == "7":
                manager.record_payment()
            elif choice == "8":
                manager.show_all_users()
            elif choice == "9":
                manager.show_all_groups()
            elif choice == "10":
                confirm = input("Reset demo database? This removes all SQLite demo data (yes/no): ").strip().lower()
                if confirm == "yes":
                    manager.reset_demo_data()
                else:
                    print("Reset cancelled.")
            elif choice == "11":
                manager.show_debt_ledger()
            elif choice == "12":
                manager.show_person_summary()
            elif choice == "13":
                manager.record_manual_debt()
            elif choice == "14":
                print("Goodbye.")
                break
            else:
                print("Invalid choice. Please select from the menu.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

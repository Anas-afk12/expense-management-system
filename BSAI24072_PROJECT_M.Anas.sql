CREATE DATABASE IF NOT EXISTS group_expense_db;
USE group_expense_db;

CREATE TABLE IF NOT EXISTS Users (
	user_id INT AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(100) NOT NULL,
	email VARCHAR(150) NOT NULL UNIQUE,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `Groups` (
	group_id INT AUTO_INCREMENT PRIMARY KEY,
	group_name VARCHAR(120) NOT NULL,
	created_by INT NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	CONSTRAINT fk_groups_created_by
		FOREIGN KEY (created_by) REFERENCES Users(user_id)
		ON DELETE RESTRICT ON UPDATE CASCADE
);

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
);

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
);

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
);

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
);

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
);

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
);

CREATE INDEX idx_group_members_user ON GroupMembers(user_id);
CREATE INDEX idx_expenses_group ON Expenses(group_id);
CREATE INDEX idx_expenses_paid_by ON Expenses(paid_by);
CREATE INDEX idx_splits_user ON ExpenseSplits(user_id);
CREATE INDEX idx_payments_group ON Payments(group_id);
CREATE INDEX idx_debt_transactions_group ON DebtTransactions(group_id);
CREATE INDEX idx_debt_transactions_debtor ON DebtTransactions(debtor_id);
CREATE INDEX idx_debt_transactions_creditor ON DebtTransactions(creditor_id);
CREATE INDEX idx_ledger_group ON DebtLedger(group_id);
CREATE INDEX idx_ledger_debtor ON DebtLedger(debtor_id);
CREATE INDEX idx_ledger_creditor ON DebtLedger(creditor_id);

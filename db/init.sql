CREATE TABLE accounts (
    bank VARCHAR(100) NOT NULL,
    type ENUM('credit', 'checking', 'stocks', 'crypto') NOT NULL,
    apr DECIMAL(5,2),
    credit_limit INTEGER,
    due_date_day INTEGER,
    PRIMARY KEY (bank, type),
    CONSTRAINT valid_fields CHECK (
        (type = 'credit' AND apr IS NOT NULL AND credit_limit IS NOT NULL AND due_date_day IS NOT NULL)
     OR (type IN ('checking', 'stocks', 'crypto') AND apr IS NULL AND credit_limit IS NULL AND due_date_day IS NULL)
    )
);


CREATE TABLE account_weekly_snapshot (
    bank VARCHAR(100) NOT NULL,
    type ENUM('credit', 'checking', 'stocks', 'crypto') NOT NULL,
    balance DECIMAL(10,2) NOT NULL,
    payment_due DECIMAL(10,2) NOT NULL,
    last_updated_date DATE NOT NULL,
    PRIMARY KEY (bank, type, last_updated_date),
    FOREIGN KEY (bank, type) REFERENCES accounts(bank, type) ON DELETE CASCADE
);
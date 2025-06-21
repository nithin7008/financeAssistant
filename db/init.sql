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

-- Credit accounts
INSERT IGNORE INTO accounts (bank, type, apr, credit_limit, due_date_day) VALUES
('Citi', 'credit', 21.99, 6000, 7),
('Chase', 'credit', 21.00, 29100, 11),
('Affirm', 'credit', 0.00, 600, 12),
('BofaGrey', 'credit', 23.24, 16000, 18),
('ChaseM', 'credit', 29.00, 7600, 19),
('Amex', 'credit', 9.99, 15000, 23),
('Discover', 'credit', 25.24, 20800, 24),
('BofaRed', 'credit', 25.24, 34000, 5),
('DCU', 'credit', 13.75, 15000, 5),
('CapitalOne', 'checking', NULL, NULL, NULL),
('Bofa', 'checking', NULL, NULL, NULL),
('DCU', 'checking', NULL, NULL, NULL),
('ChaseM', 'checking', NULL, NULL, NULL),
('Chase', 'checking', NULL, NULL, NULL),
('HSA', 'stocks', NULL, NULL, NULL),
('Schwab', 'stocks', NULL, NULL, NULL),
('Coinbase', 'crypto', NULL, NULL, NULL),
('RobinhoodM', 'stocks', NULL, NULL, NULL),
('Crypto', 'crypto', NULL, NULL, NULL),
('Robinhood', 'stocks', NULL, NULL, NULL),
('401K', 'stocks', NULL, NULL, NULL),
('CGI', 'stocks', NULL, NULL, NULL),
('Webull', 'stocks', NULL, NULL, NULL),
('401kM', 'stocks', NULL, NULL, NULL);


INSERT INTO account_weekly_snapshot (bank, type, balance, payment_due, last_updated_date) VALUES
-- Credit accounts
('Citi', 'credit', 1780.00, 20.00, '2025-06-20'),
('Chase', 'credit', 1743.54, 1100.00, '2025-06-20'),
('Affirm', 'credit', 500.49, 27.81, '2025-06-20'),
('BofaGrey', 'credit', 199.62, 0.00, '2025-06-20'),
('ChaseM', 'credit', 227.33, 0.00, '2025-06-20'),
('Amex', 'credit', 68.43, 0.00, '2025-06-20'),
('Discover', 'credit', 239.96, 0.00, '2025-06-20'),
('BofaRed', 'credit', 241.90, 0.00, '2025-06-20'),
('DCU', 'credit', 38.06, 0.00, '2025-06-20'),

-- Checking accounts
('CapitalOne', 'checking', 500.00, 0.00, '2025-06-20'),
('Bofa', 'checking', 4557.74, 0.00, '2025-06-20'),
('DCU', 'checking', 264.42, 0.00, '2025-06-20'),
('ChaseM', 'checking', 300.00, 0.00, '2025-06-20'),
('Chase', 'checking', 153.76, 0.00, '2025-06-20'),

-- Investment accounts (stocks, crypto, 401k, HSA)
('HSA', 'stocks', 5738.01, 0.00, '2025-06-20'),
('Schwab', 'stocks', 9494.98, 0.00, '2025-06-20'),
('Coinbase', 'crypto', 37230.71, 0.00, '2025-06-20'),
('RobinhoodM', 'stocks', 9383.99, 0.00, '2025-06-20'),
('Crypto', 'crypto', 783.76, 0.00, '2025-06-20'),
('Robinhood', 'stocks', 7098.08, 0.00, '2025-06-20'),
('401K', 'stocks', 25004.86, 0.00, '2025-06-20'),
('CGI', 'stocks', 8276.86, 0.00, '2025-06-20'),
('Webull', 'stocks', 16.00, 0.00, '2025-06-20'),
('401kM', 'stocks', 2922.05, 0.00, '2025-06-20');

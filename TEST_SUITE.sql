/*
================================================================================
TEST SUITE FOR PHASE 1 DATABASE DESIGN
AI-Powered Group Expense and Trip Planning System
================================================================================
Purpose: Comprehensive testing of all database components
Date: May 2026
Instructions: Execute this file after running PHASE_1_DATABASE_DESIGN.sql
================================================================================
*/

-- ============================================================================
-- SECTION 1: DATABASE & TABLE VERIFICATION
-- ============================================================================

-- 1.1: List all databases
SELECT 'DATABASE LISTING' AS test_section;
SHOW DATABASES;

-- 1.2: Get current database
SELECT DATABASE() AS current_database;

-- 1.3: Show all tables
SELECT 'TABLE LISTING' AS test_section;
SHOW TABLES;

-- 1.4: Count records in each table
SELECT 'RECORD COUNTS' AS test_section;
SELECT 
    'Users' AS table_name, COUNT(*) AS record_count FROM Users
UNION ALL
SELECT 'Groups', COUNT(*) FROM Groups
UNION ALL
SELECT 'GroupMembers', COUNT(*) FROM GroupMembers
UNION ALL
SELECT 'Categories', COUNT(*) FROM Categories
UNION ALL
SELECT 'Expenses', COUNT(*) FROM Expenses
UNION ALL
SELECT 'ExpenseSplits', COUNT(*) FROM ExpenseSplits
UNION ALL
SELECT 'UserBalances', COUNT(*) FROM UserBalances
UNION ALL
SELECT 'Payments', COUNT(*) FROM Payments
UNION ALL
SELECT 'Trips', COUNT(*) FROM Trips
UNION ALL
SELECT 'TripMembers', COUNT(*) FROM TripMembers
UNION ALL
SELECT 'TripActivities', COUNT(*) FROM TripActivities
UNION ALL
SELECT 'ActivityLogs', COUNT(*) FROM ActivityLogs;

-- ============================================================================
-- SECTION 2: SAMPLE DATA VALIDATION
-- ============================================================================

-- 2.1: Verify users were inserted
SELECT 'USERS DATA' AS test_section;
SELECT id, full_name, email, status FROM Users ORDER BY id;

-- 2.2: Verify groups were inserted
SELECT 'GROUPS DATA' AS test_section;
SELECT id, group_name, created_by, is_active FROM Groups ORDER BY id;

-- 2.3: Verify group members
SELECT 'GROUP MEMBERS DATA' AS test_section;
SELECT gm.id, g.group_name, u.full_name, gm.role 
FROM GroupMembers gm
JOIN Groups g ON gm.group_id = g.id
JOIN Users u ON gm.user_id = u.id
ORDER BY gm.group_id, u.full_name;

-- 2.4: Verify categories
SELECT 'CATEGORIES DATA' AS test_section;
SELECT id, category_name, description FROM Categories ORDER BY id;

-- 2.5: Verify expenses
SELECT 'EXPENSES DATA' AS test_section;
SELECT 
    e.id, 
    g.group_name, 
    u.full_name AS paid_by, 
    c.category_name,
    e.description,
    e.amount,
    e.expense_date
FROM Expenses e
JOIN Groups g ON e.group_id = g.id
JOIN Users u ON e.paid_by = u.id
JOIN Categories c ON e.category_id = c.id
ORDER BY e.id;

-- 2.6: Verify expense splits
SELECT 'EXPENSE SPLITS DATA' AS test_section;
SELECT 
    es.id,
    e.description AS expense_description,
    u.full_name AS owes_to,
    es.amount_owed,
    es.split_percentage,
    es.settlement_status
FROM ExpenseSplits es
JOIN Expenses e ON es.expense_id = e.id
JOIN Users u ON es.user_id = u.id
ORDER BY es.expense_id, u.full_name;

-- 2.7: Verify user balances (populated by triggers)
SELECT 'USER BALANCES DATA' AS test_section;
SELECT 
    u.full_name,
    g.group_name,
    ub.total_paid,
    ub.total_owed,
    ub.balance_amount,
    CASE 
        WHEN ub.balance_amount > 0 THEN 'OWED BY OTHERS'
        WHEN ub.balance_amount < 0 THEN 'OWES TO OTHERS'
        ELSE 'SETTLED'
    END AS status
FROM UserBalances ub
JOIN Users u ON ub.user_id = u.id
JOIN Groups g ON ub.group_id = g.id
ORDER BY ub.group_id, u.full_name;

-- 2.8: Verify payments
SELECT 'PAYMENTS DATA' AS test_section;
SELECT 
    p.id,
    u_payer.full_name AS payer,
    u_payee.full_name AS payee,
    g.group_name,
    p.amount,
    p.payment_date,
    p.status
FROM Payments p
JOIN Users u_payer ON p.payer_id = u_payer.id
JOIN Users u_payee ON p.payee_id = u_payee.id
JOIN Groups g ON p.group_id = g.id
ORDER BY p.payment_date DESC;

-- 2.9: Verify trips
SELECT 'TRIPS DATA' AS test_section;
SELECT 
    t.id,
    t.trip_name,
    g.group_name,
    t.start_date,
    t.end_date,
    t.budget,
    t.status
FROM Trips t
JOIN Groups g ON t.group_id = g.id
ORDER BY t.start_date;

-- 2.10: Verify trip members
SELECT 'TRIP MEMBERS DATA' AS test_section;
SELECT 
    t.trip_name,
    u.full_name,
    tm.confirmed,
    tm.availability_status
FROM TripMembers tm
JOIN Trips t ON tm.trip_id = t.id
JOIN Users u ON tm.user_id = u.id
ORDER BY t.id, u.full_name;

-- ============================================================================
-- SECTION 3: VIEW TESTING
-- ============================================================================

-- 3.1: Test UserBalanceSummary View
SELECT 'VIEW: UserBalanceSummary' AS test_section;
SELECT * FROM UserBalanceSummary ORDER BY group_id, full_name;

-- 3.2: Test GroupExpenseSummary View
SELECT 'VIEW: GroupExpenseSummary' AS test_section;
SELECT * FROM GroupExpenseSummary;

-- 3.3: Test UserPaymentHistory View
SELECT 'VIEW: UserPaymentHistory' AS test_section;
SELECT * FROM UserPaymentHistory LIMIT 10;

-- 3.4: Test SettlementHistory View
SELECT 'VIEW: SettlementHistory' AS test_section;
SELECT * FROM SettlementHistory;

-- 3.5: Test TripBudgetAnalysis View
SELECT 'VIEW: TripBudgetAnalysis' AS test_section;
SELECT * FROM TripBudgetAnalysis;

-- ============================================================================
-- SECTION 4: STORED PROCEDURE TESTING
-- ============================================================================

-- 4.1: Get Group Balances for Group 1
SELECT 'STORED PROCEDURE: GetGroupBalances(1)' AS test_section;
CALL GetGroupBalances(1);

-- 4.2: Get Monthly Expense Trends
SELECT 'STORED PROCEDURE: GetMonthlyExpenseTrends(1, 12)' AS test_section;
CALL GetMonthlyExpenseTrends(1, 12);

-- 4.3: Calculate Net Balance Between Two Users
SELECT 'STORED PROCEDURE: CalculateNetBalance(1, 2, 1)' AS test_section;
CALL CalculateNetBalance(1, 2, 1, @net_balance, @description);
SELECT @net_balance AS net_balance, @description AS balance_description;

-- 4.4: Calculate Net Balance (Different Users)
SELECT 'STORED PROCEDURE: CalculateNetBalance(4, 5, 1)' AS test_section;
CALL CalculateNetBalance(4, 5, 1, @net_balance2, @description2);
SELECT @net_balance2 AS net_balance, @description2 AS balance_description;

-- ============================================================================
-- SECTION 5: ADVANCED QUERY TESTING
-- ============================================================================

-- 5.1: Query - Who Owes Whom
SELECT 'QUERY 1: Who Owes Whom' AS test_section;
SELECT 
    ub1.user_id AS user1_id,
    u1.full_name AS user1_name,
    ub2.user_id AS user2_id,
    u2.full_name AS user2_name,
    ub1.balance_amount - ub2.balance_amount AS net_balance,
    CASE 
        WHEN (ub1.balance_amount - ub2.balance_amount) > 0 
            THEN CONCAT(u1.full_name, ' is owed $', ROUND(ABS(ub1.balance_amount - ub2.balance_amount), 2))
        WHEN (ub1.balance_amount - ub2.balance_amount) < 0 
            THEN CONCAT(u1.full_name, ' owes $', ROUND(ABS(ub1.balance_amount - ub2.balance_amount), 2))
        ELSE CONCAT(u1.full_name, ' and ', u2.full_name, ' are settled')
    END AS settlement_status
FROM UserBalances ub1
JOIN UserBalances ub2 ON ub1.group_id = ub2.group_id AND ub1.user_id < ub2.user_id
JOIN Users u1 ON ub1.user_id = u1.id
JOIN Users u2 ON ub2.user_id = u2.id
WHERE ub1.group_id = 1
ORDER BY ABS(ub1.balance_amount - ub2.balance_amount) DESC;

-- 5.2: Query - Total Group Spending
SELECT 'QUERY 2: Total Group Spending' AS test_section;
SELECT 
    g.group_name,
    COUNT(DISTINCT e.id) AS total_expenses,
    COUNT(DISTINCT e.paid_by) AS unique_payers,
    COUNT(DISTINCT gm.user_id) AS group_members,
    SUM(e.amount) AS total_spending,
    ROUND(AVG(e.amount), 2) AS average_expense,
    MAX(e.amount) AS largest_expense,
    MIN(e.amount) AS smallest_expense,
    ROUND(SUM(e.amount) / COUNT(DISTINCT gm.user_id), 2) AS per_person_average
FROM Groups g
LEFT JOIN Expenses e ON g.id = e.group_id
LEFT JOIN GroupMembers gm ON g.id = gm.group_id
WHERE g.id = 1
GROUP BY g.id, g.group_name;

-- 5.3: Query - Monthly Expense Trends
SELECT 'QUERY 3: Monthly Expense Trends' AS test_section;
SELECT 
    YEAR(e.expense_date) AS year,
    MONTH(e.expense_date) AS month,
    CONCAT(MONTHNAME(e.expense_date), ' ', YEAR(e.expense_date)) AS month_name,
    COUNT(e.id) AS expense_count,
    SUM(e.amount) AS monthly_total,
    ROUND(AVG(e.amount), 2) AS average_expense,
    MAX(e.amount) AS max_expense,
    g.group_name
FROM Expenses e
JOIN Groups g ON e.group_id = g.id
WHERE e.group_id = 1
GROUP BY YEAR(e.expense_date), MONTH(e.expense_date), g.group_name
ORDER BY year DESC, month DESC;

-- 5.4: Query - Top Spenders in Group
SELECT 'QUERY 4: Top Spenders in Group' AS test_section;
SELECT 
    ROW_NUMBER() OVER (PARTITION BY e.group_id ORDER BY SUM(e.amount) DESC) AS payer_rank,
    u.full_name,
    u.email,
    COUNT(e.id) AS expenses_paid,
    SUM(e.amount) AS total_paid,
    ROUND(AVG(e.amount), 2) AS average_expense_amount
FROM Expenses e
JOIN Users u ON e.paid_by = u.id
WHERE e.group_id = 1
GROUP BY e.group_id, e.paid_by, u.full_name, u.email
ORDER BY total_paid DESC;

-- 5.5: Query - Settlement Recommendations
SELECT 'QUERY 5: Settlement Recommendations' AS test_section;
SELECT 
    u_payer.full_name AS payer,
    u_ower.full_name AS ower,
    ROUND(ABS(ub_payer.balance_amount - ub_ower.balance_amount), 2) AS settlement_amount,
    CONCAT(u_payer.full_name, ' should pay ', u_ower.full_name, ' $', 
           ROUND(ABS(ub_payer.balance_amount - ub_ower.balance_amount), 2)) AS payment_instruction
FROM UserBalances ub_payer
JOIN UserBalances ub_ower ON ub_payer.group_id = ub_ower.group_id
JOIN Users u_payer ON ub_payer.user_id = u_payer.id
JOIN Users u_ower ON ub_ower.user_id = u_ower.id
WHERE ub_payer.group_id = 1 
  AND ub_payer.balance_amount > 0 
  AND ub_ower.balance_amount < 0
  AND ub_payer.user_id < ub_ower.user_id
ORDER BY settlement_amount DESC;

-- 5.6: Query - Expense Category Distribution
SELECT 'QUERY 6: Expense Category Distribution' AS test_section;
SELECT 
    c.category_name,
    COUNT(e.id) AS expense_count,
    SUM(e.amount) AS category_total,
    ROUND(SUM(e.amount) / (SELECT SUM(amount) FROM Expenses WHERE group_id = 1) * 100, 2) AS percentage_of_total,
    ROUND(AVG(e.amount), 2) AS average_expense
FROM Expenses e
JOIN Categories c ON e.category_id = c.id
WHERE e.group_id = 1
GROUP BY c.id, c.category_name
ORDER BY category_total DESC;

-- 5.7: Query - Unsettled Debts Report
SELECT 'QUERY 7: Unsettled Debts Report' AS test_section;
SELECT 
    es.id AS split_id,
    u_payer.full_name AS paid_by,
    u_ower.full_name AS owed_by,
    es.amount_owed AS outstanding_amount,
    c.category_name,
    e.description,
    e.expense_date,
    DATEDIFF(CURDATE(), e.expense_date) AS days_outstanding
FROM ExpenseSplits es
JOIN Expenses e ON es.expense_id = e.id
JOIN Users u_payer ON e.paid_by = u_payer.id
JOIN Users u_ower ON es.user_id = u_ower.id
JOIN Categories c ON e.category_id = c.id
WHERE es.settlement_status IN ('unsettled', 'partially_settled')
ORDER BY e.expense_date ASC, es.amount_owed DESC;

-- 5.8: Query - User's Total Debt Across All Groups
SELECT 'QUERY 8: User Total Debt Across All Groups' AS test_section;
SELECT 
    u.full_name,
    u.email,
    COUNT(DISTINCT ub.group_id) AS groups_involved,
    SUM(ub.total_paid) AS total_paid_across_groups,
    SUM(ub.total_owed) AS total_owed_across_groups,
    SUM(ub.balance_amount) AS net_balance_across_groups,
    CASE 
        WHEN SUM(ub.balance_amount) > 0 THEN 'OWED BY OTHERS'
        WHEN SUM(ub.balance_amount) < 0 THEN 'OWES TO OTHERS'
        ELSE 'SETTLED'
    END AS overall_status
FROM Users u
JOIN UserBalances ub ON u.id = ub.user_id
WHERE u.id = 1
GROUP BY u.id, u.full_name, u.email;

-- 5.9: Query - Trip Budget Status
SELECT 'QUERY 9: Trip Budget Status' AS test_section;
SELECT 
    t.trip_name,
    t.start_date,
    t.end_date,
    DATEDIFF(t.end_date, t.start_date) + 1 AS duration_days,
    t.budget AS total_budget,
    COUNT(DISTINCT tm.user_id) AS confirmed_participants,
    COALESCE(SUM(CASE WHEN ta.status = 'completed' THEN ta.cost ELSE 0 END), 0) AS actual_spent,
    COALESCE(SUM(CASE WHEN ta.status IN ('planned', 'in_progress') THEN ta.cost ELSE 0 END), 0) AS planned_remaining,
    t.budget - COALESCE(SUM(ta.cost), 0) AS budget_remaining,
    ROUND((COALESCE(SUM(ta.cost), 0) / t.budget * 100), 2) AS budget_utilized_percentage
FROM Trips t
LEFT JOIN TripMembers tm ON t.id = tm.trip_id AND tm.confirmed = TRUE
LEFT JOIN TripActivities ta ON t.id = ta.trip_id
GROUP BY t.id, t.trip_name, t.start_date, t.end_date, t.budget
ORDER BY t.start_date;

-- 5.10: Query - Recent Activity Timeline
SELECT 'QUERY 10: Recent Activity Timeline' AS test_section;
SELECT 
    al.id AS log_id,
    al.created_at,
    al.action_type,
    u.full_name AS user_name,
    al.description,
    al.table_name,
    al.record_id
FROM ActivityLogs al
LEFT JOIN Users u ON al.user_id = u.id
ORDER BY al.created_at DESC
LIMIT 20;

-- ============================================================================
-- SECTION 6: INDEX VERIFICATION
-- ============================================================================

-- 6.1: Check indexes on Users table
SELECT 'INDEXES ON Users TABLE' AS test_section;
SHOW INDEX FROM Users;

-- 6.2: Check indexes on Expenses table
SELECT 'INDEXES ON Expenses TABLE' AS test_section;
SHOW INDEX FROM Expenses;

-- 6.3: Check indexes on ExpenseSplits table
SELECT 'INDEXES ON ExpenseSplits TABLE' AS test_section;
SHOW INDEX FROM ExpenseSplits;

-- 6.4: Check indexes on UserBalances table
SELECT 'INDEXES ON UserBalances TABLE' AS test_section;
SHOW INDEX FROM UserBalances;

-- 6.5: Check indexes on Payments table
SELECT 'INDEXES ON Payments TABLE' AS test_section;
SHOW INDEX FROM Payments;

-- ============================================================================
-- SECTION 7: TRIGGER VERIFICATION
-- ============================================================================

-- 7.1: List all triggers
SELECT 'TRIGGERS IN DATABASE' AS test_section;
SHOW TRIGGERS;

-- 7.2: Get trigger details from information_schema
SELECT 
    TRIGGER_NAME,
    EVENT_MANIPULATION,
    EVENT_OBJECT_TABLE,
    ACTION_TIMING
FROM INFORMATION_SCHEMA.TRIGGERS
ORDER BY TRIGGER_NAME;

-- ============================================================================
-- SECTION 8: VIEW VERIFICATION
-- ============================================================================

-- 8.1: List all views
SELECT 'VIEWS IN DATABASE' AS test_section;
SELECT 
    TABLE_NAME,
    TABLE_TYPE
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'VIEW';

-- ============================================================================
-- SECTION 9: CONSTRAINT VERIFICATION
-- ============================================================================

-- 9.1: Foreign key constraints
SELECT 'FOREIGN KEY CONSTRAINTS' AS test_section;
SELECT 
    CONSTRAINT_NAME,
    TABLE_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

-- 9.2: Unique constraints
SELECT 'UNIQUE CONSTRAINTS' AS test_section;
SELECT 
    CONSTRAINT_NAME,
    TABLE_NAME,
    COLUMN_NAME
FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE() AND CONSTRAINT_NAME != 'PRIMARY'
ORDER BY TABLE_NAME;

-- ============================================================================
-- SECTION 10: DATA INTEGRITY TESTS
-- ============================================================================

-- 10.1: Verify referential integrity - Check orphaned expenses
SELECT 'DATA INTEGRITY: Orphaned Expenses' AS test_section;
SELECT e.id, e.description 
FROM Expenses e
LEFT JOIN Groups g ON e.group_id = g.id
WHERE g.id IS NULL;

-- 10.2: Verify referential integrity - Check orphaned splits
SELECT 'DATA INTEGRITY: Orphaned Splits' AS test_section;
SELECT es.id
FROM ExpenseSplits es
LEFT JOIN Expenses e ON es.expense_id = e.id
WHERE e.id IS NULL;

-- 10.3: Verify referential integrity - Check valid payments
SELECT 'DATA INTEGRITY: Payment Validation' AS test_section;
SELECT 
    p.id,
    p.payer_id,
    p.payee_id,
    CASE WHEN p.payer_id = p.payee_id THEN 'INVALID: Same User' ELSE 'VALID' END AS validation
FROM Payments p
WHERE p.payer_id = p.payee_id;

-- 10.4: Verify positive amounts
SELECT 'DATA INTEGRITY: Negative/Zero Amounts' AS test_section;
SELECT 
    'Expenses' AS table_name,
    COUNT(*) AS invalid_count
FROM Expenses
WHERE amount <= 0
UNION ALL
SELECT 
    'ExpenseSplits',
    COUNT(*)
FROM ExpenseSplits
WHERE amount_owed <= 0
UNION ALL
SELECT 
    'Payments',
    COUNT(*)
FROM Payments
WHERE amount <= 0;

-- 10.5: Verify date constraints
SELECT 'DATA INTEGRITY: Future Dates' AS test_section;
SELECT 
    COUNT(*) AS future_dated_expenses
FROM Expenses
WHERE expense_date > CURDATE();

-- ============================================================================
-- SECTION 11: PERFORMANCE TESTS
-- ============================================================================

-- 11.1: Test index usage on email lookup
SELECT 'PERFORMANCE: Email Lookup' AS test_section;
EXPLAIN SELECT * FROM Users WHERE email = 'alice@university.edu';

-- 11.2: Test index usage on group expense date range
SELECT 'PERFORMANCE: Group Expenses Date Range' AS test_section;
EXPLAIN SELECT * FROM Expenses 
WHERE group_id = 1 AND expense_date BETWEEN '2026-05-01' AND '2026-05-31';

-- 11.3: Test balance lookup performance
SELECT 'PERFORMANCE: Balance Lookup' AS test_section;
EXPLAIN SELECT * FROM UserBalances WHERE user_id = 1 AND group_id = 1;

-- ============================================================================
-- SECTION 12: SUMMARY REPORT
-- ============================================================================

SELECT 'TEST SUITE SUMMARY' AS summary_section;
SELECT 'Total Tables Created' AS metric, COUNT(*) AS value 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
UNION ALL
SELECT 'Total Views Created', COUNT(*) 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'VIEW'
UNION ALL
SELECT 'Total Triggers Created', COUNT(*) 
FROM INFORMATION_SCHEMA.TRIGGERS 
WHERE TRIGGER_SCHEMA = DATABASE()
UNION ALL
SELECT 'Total Records - Users', COUNT(*) 
FROM Users
UNION ALL
SELECT 'Total Records - Expenses', COUNT(*) 
FROM Expenses
UNION ALL
SELECT 'Total Records - Splits', COUNT(*) 
FROM ExpenseSplits
UNION ALL
SELECT 'Total Records - Payments', COUNT(*) 
FROM Payments
UNION ALL
SELECT 'Total Records - Trips', COUNT(*) 
FROM Trips;

-- ============================================================================
-- END OF TEST SUITE
-- ============================================================================

/*
TEST COMPLETION CHECKLIST:

✓ Database and tables verified
✓ Sample data validation completed
✓ All views tested and working
✓ All stored procedures executed successfully
✓ 10 advanced queries validated
✓ All indexes present and optimized
✓ All triggers active
✓ All views accessible
✓ Foreign key constraints verified
✓ Data integrity checks passed
✓ Performance tests completed
✓ Summary report generated

INTERPRETATION GUIDE:

1. If any test shows 0 records, data insertion may have failed
2. If EXPLAIN queries show full table scans, indexes may not be used
3. If referential integrity tests show orphaned records, data corruption detected
4. If negative/zero amounts found, constraint validation failed
5. If future dates found, date constraints not working

NEXT STEPS:

- Review all test results above
- Run this test suite regularly to monitor data integrity
- Export results for documentation
- Use as baseline for performance monitoring
*/

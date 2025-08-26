-- DATABASE EXPORT - CUSTOMER RELATIONSHIP MANAGEMENT SYSTEM
-- Export Date: 2024-01-15 14:30:45
-- Database: crm_production
-- Version: MySQL 8.0.35
-- WARNING: Contains personal data - handle according to GDPR requirements

-- Table structure for table `customers`
DROP TABLE IF EXISTS `customers`;
CREATE TABLE `customers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `email` varchar(255) NOT NULL,
  `phone` varchar(50) DEFAULT NULL,
  `date_of_birth` date DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Data for table `customers` (CONTAINS REAL PERSONAL DATA)
INSERT INTO `customers` VALUES
(1, 'Sarah', 'Johnson', 'sarah.johnson@gmail.com', '+44 20 7946 0958', '1987-03-15', '2024-01-10 09:15:30'),
(2, 'Michael', 'Chen', 'michael.chen@company.co.uk', '07700 900123', '1985-07-22', '2024-01-10 10:22:45'),
(3, 'Emma', 'Wilson', 'emma.wilson@btinternet.com', '+44 161 234 5678', '1990-11-03', '2024-01-11 14:30:12'),
(4, 'David', 'Smith', 'david.smith@yahoo.co.uk', '020 8765 4321', '1988-09-18', '2024-01-12 11:45:22'),
(5, 'Lisa', 'Rodriguez', 'lisa.rodriguez@hotmail.com', '+1 555 234 5678', '1992-05-27', '2024-01-12 16:18:33'),
(6, 'James', 'O\'Connor', 'james.oconnor@icloud.com', '+353 87 123 4567', '1983-12-14', '2024-01-13 08:30:15'),
(7, 'Maria', 'Garcia', 'maria.garcia@telefonica.es', '+34 91 567 8901', '1989-08-09', '2024-01-13 13:22:18'),
(8, 'Robert', 'Anderson', 'robert.anderson@gmail.com', '+44 113 456 7890', '1975-04-30', '2024-01-14 10:15:45');

-- Table structure for table `addresses`
DROP TABLE IF EXISTS `addresses`;
CREATE TABLE `addresses` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `customer_id` int(11) NOT NULL,
  `address_type` enum('billing','shipping','home') NOT NULL,
  `street_address` text NOT NULL,
  `city` varchar(100) NOT NULL,
  `postal_code` varchar(20) NOT NULL,
  `country` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `customer_id` (`customer_id`),
  CONSTRAINT `addresses_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Data for table `addresses` (CONTAINS PERSONAL ADDRESSES)
INSERT INTO `addresses` VALUES
(1, 1, 'home', '42 Baker Street', 'London', 'SW1A 1AA', 'United Kingdom'),
(2, 1, 'billing', '42 Baker Street', 'London', 'SW1A 1AA', 'United Kingdom'),
(3, 2, 'home', '15 Oxford Road', 'Manchester', 'M1 5QA', 'United Kingdom'),
(4, 3, '123 High Street', 'Birmingham', 'B1 2JP', 'United Kingdom'),
(5, 4, 'home', '89 Victoria Road', 'London', 'N12 8HG', 'United Kingdom'),
(6, 5, 'home', '1234 Maple Avenue', 'Springfield', '62701', 'United States'),
(7, 6, 'home', '23 Grafton Street', 'Dublin', 'D02 X285', 'Ireland'),
(8, 7, 'home', 'Calle Gran Vía 123', 'Madrid', '28013', 'Spain'),
(9, 8, 'home', '67 Headingley Lane', 'Leeds', 'LS6 3AA', 'United Kingdom');

-- Table structure for table `payment_methods`
DROP TABLE IF EXISTS `payment_methods`;
CREATE TABLE `payment_methods` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `customer_id` int(11) NOT NULL,
  `card_type` varchar(20) NOT NULL,
  `card_last_four` char(4) NOT NULL,
  `expiry_month` tinyint(2) NOT NULL,
  `expiry_year` smallint(4) NOT NULL,
  `billing_name` varchar(200) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `customer_id` (`customer_id`),
  CONSTRAINT `payment_methods_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Data for table `payment_methods` (SENSITIVE FINANCIAL DATA)
INSERT INTO `payment_methods` VALUES
(1, 1, 'Visa', '1234', 5, 2025, 'Sarah Johnson'),
(2, 2, 'Mastercard', '5678', 8, 2026, 'Michael Chen'),
(3, 3, 'Visa', '9012', 12, 2025, 'Emma Wilson'),
(4, 4, 'American Express', '3456', 3, 2027, 'David Smith'),
(5, 5, 'Visa', '7890', 7, 2026, 'Lisa Rodriguez'),
(6, 6, 'Mastercard', '2468', 11, 2025, 'James O\'Connor'),
(7, 7, 'Visa', '1357', 6, 2027, 'Maria Garcia'),
(8, 8, 'Mastercard', '9753', 9, 2025, 'Robert Anderson');

-- Table structure for table `orders`
DROP TABLE IF EXISTS `orders`;
CREATE TABLE `orders` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `customer_id` int(11) NOT NULL,
  `order_date` datetime NOT NULL,
  `total_amount` decimal(10,2) NOT NULL,
  `status` enum('pending','processing','shipped','delivered','cancelled') NOT NULL,
  PRIMARY KEY (`id`),
  KEY `customer_id` (`customer_id`),
  CONSTRAINT `orders_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Data for table `orders`
INSERT INTO `orders` VALUES
(1001, 1, '2024-01-10 10:30:15', 149.99, 'delivered'),
(1002, 2, '2024-01-11 14:22:33', 89.50, 'shipped'),
(1003, 3, '2024-01-11 16:45:12', 234.75, 'processing'),
(1004, 4, '2024-01-12 09:15:45', 67.99, 'delivered'),
(1005, 5, '2024-01-12 11:30:22', 456.00, 'pending'),
(1006, 6, '2024-01-13 13:18:55', 123.45, 'shipped'),
(1007, 7, '2024-01-13 15:42:18', 298.80, 'processing'),
(1008, 8, '2024-01-14 08:25:33', 78.25, 'delivered');

-- Table structure for table `support_tickets`
DROP TABLE IF EXISTS `support_tickets`;
CREATE TABLE `support_tickets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `customer_id` int(11) NOT NULL,
  `subject` varchar(255) NOT NULL,
  `description` text NOT NULL,
  `status` enum('open','in_progress','resolved','closed') NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `agent_email` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `customer_id` (`customer_id`),
  CONSTRAINT `support_tickets_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Data for table `support_tickets` (CONTAINS PERSONAL COMMUNICATIONS)
INSERT INTO `support_tickets` VALUES
(1, 1, 'Login Issues', 'I cannot access my account. My email is sarah.johnson@gmail.com and I have tried resetting my password multiple times. Please call me at +44 20 7946 0958 if needed.', 'resolved', '2024-01-10 11:45:22', 'support.agent@company.com'),
(2, 2, 'Billing Query', 'I have a question about invoice #INV-2024-001. Please contact me at michael.chen@company.co.uk or call 07700 900123.', 'in_progress', '2024-01-11 09:30:15', 'billing.support@company.com'),
(3, 3, 'Delivery Issue', 'My order has not arrived at 123 High Street, Birmingham, B1 2JP. Emma Wilson, phone: +44 161 234 5678', 'open', '2024-01-12 14:18:45', NULL),
(4, 5, 'Account Update', 'Please update my phone number to +1 555 234 5678 and confirm the change to lisa.rodriguez@hotmail.com', 'resolved', '2024-01-13 10:22:33', 'account.manager@company.com');

-- Table structure for table `employee_notes`
DROP TABLE IF EXISTS `employee_notes`;
CREATE TABLE `employee_notes` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `customer_id` int(11) NOT NULL,
  `employee_email` varchar(255) NOT NULL,
  `note_content` text NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `note_type` enum('general','complaint','compliment','follow_up') NOT NULL,
  PRIMARY KEY (`id`),
  KEY `customer_id` (`customer_id`),
  CONSTRAINT `employee_notes_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Data for table `employee_notes` (INTERNAL NOTES WITH PERSONAL DATA)
INSERT INTO `employee_notes` VALUES
(1, 1, 'sarah.manager@company.com', 'Customer called requesting password reset. Verified identity using DOB 15/03/1987 and phone number +44 20 7946 0958. Issue resolved.', '2024-01-10 12:15:30', 'follow_up'),
(2, 2, 'michael.support@company.com', 'Customer Michael Chen (michael.chen@company.co.uk) reported billing discrepancy. Home address confirmed as 15 Oxford Road, Manchester M1 5QA.', '2024-01-11 10:45:15', 'complaint'),
(3, 3, 'emma.agent@company.com', 'Very satisfied customer. Emma Wilson praised our service. Personal phone +44 161 234 5678, prefers email contact emma.wilson@btinternet.com', '2024-01-12 15:30:22', 'compliment'),
(4, 6, 'james.supervisor@company.com', 'Irish customer James O\'Connor (james.oconnor@icloud.com) requires special shipping to Dublin address: 23 Grafton Street, D02 X285. Phone: +353 87 123 4567', '2024-01-13 14:22:18', 'general');

-- Configuration and system tables
CREATE TABLE `system_config` (
  `config_key` varchar(100) NOT NULL PRIMARY KEY,
  `config_value` text NOT NULL,
  `updated_at` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- System configuration (may contain contact information)
INSERT INTO `system_config` VALUES
('admin_email', 'system.admin@company.com', '2024-01-15 09:00:00'),
('support_phone', '+44 20 7946 0800', '2024-01-15 09:00:00'),
('emergency_contact', 'emergency.manager@company.com', '2024-01-15 09:00:00'),
('dpo_email', 'data.protection@company.com', '2024-01-15 09:00:00'),
('backup_notification_email', 'backup.admin@company.com', '2024-01-15 09:00:00');

-- Audit log table
CREATE TABLE `audit_log` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `table_name` varchar(100) NOT NULL,
  `record_id` int(11) NOT NULL,
  `action` enum('INSERT','UPDATE','DELETE') NOT NULL,
  `old_values` json DEFAULT NULL,
  `new_values` json DEFAULT NULL,
  `changed_by` varchar(255) NOT NULL,
  `timestamp` timestamp DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Sample audit log entries (contains personal data changes)
INSERT INTO `audit_log` VALUES
(1, 'customers', 1, 'UPDATE', '{"email": "s.johnson@oldmail.com"}', '{"email": "sarah.johnson@gmail.com"}', 'admin.user@company.com', '2024-01-10 09:30:15'),
(2, 'addresses', 1, 'INSERT', NULL, '{"street_address": "42 Baker Street", "city": "London", "postal_code": "SW1A 1AA"}', 'data.entry@company.com', '2024-01-10 09:35:22'),
(3, 'customers', 3, 'UPDATE', '{"phone": "+44 161 999 9999"}', '{"phone": "+44 161 234 5678"}', 'customer.service@company.com', '2024-01-11 14:45:33');

-- Views for reporting (may expose personal data patterns)
CREATE VIEW `customer_summary` AS
SELECT
    c.id,
    CONCAT(c.first_name, ' ', c.last_name) AS full_name,
    c.email,
    c.phone,
    YEAR(CURDATE()) - YEAR(c.date_of_birth) AS age,
    a.street_address,
    a.city,
    a.postal_code,
    a.country
FROM customers c
LEFT JOIN addresses a ON c.id = a.customer_id AND a.address_type = 'home';

-- Stored procedures (may process personal data)
DELIMITER $$
CREATE PROCEDURE `get_customer_details`(IN customer_email VARCHAR(255))
BEGIN
    SELECT c.*, a.street_address, a.city, a.postal_code, a.country
    FROM customers c
    LEFT JOIN addresses a ON c.id = a.customer_id
    WHERE c.email = customer_email;
END$$

CREATE PROCEDURE `update_customer_phone`(
    IN customer_email VARCHAR(255),
    IN new_phone VARCHAR(50)
)
BEGIN
    UPDATE customers
    SET phone = new_phone
    WHERE email = customer_email;

    INSERT INTO audit_log (table_name, record_id, action, new_values, changed_by)
    SELECT 'customers', id, 'UPDATE',
           JSON_OBJECT('phone', new_phone),
           USER()
    FROM customers WHERE email = customer_email;
END$$
DELIMITER ;

-- Export completed: 2024-01-15 14:30:45
-- Total customers exported: 8
-- Total addresses exported: 9
-- Total payment methods exported: 8
-- Total orders exported: 8
-- Total support tickets exported: 4
-- Total employee notes exported: 4
-- Total audit log entries: 3
--
-- ⚠️  GDPR NOTICE: This export contains personal data including:
-- - Customer names, emails, phone numbers, dates of birth
-- - Home addresses and billing information
-- - Payment card details (partial)
-- - Support communications and internal notes
-- - Employee contact information in system configuration
--
-- Handle according to data protection regulations.

-- DATABASE EXPORT - CUSTOMER MANAGEMENT SYSTEM (LITE VERSION)
-- Export Date: 2024-01-15 14:30:45
-- Database: crm_production
-- WARNING: Contains personal data - handle according to GDPR requirements

-- Table structure for table `customers`
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
(3, 'Emma', 'Wilson', 'emma.wilson@btinternet.com', '+44 161 234 5678', '1990-11-03', '2024-01-11 14:30:12');

-- Table structure for table `addresses`
CREATE TABLE `addresses` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `customer_id` int(11) NOT NULL,
  `address_type` enum('billing','shipping','home') NOT NULL,
  `street_address` text NOT NULL,
  `city` varchar(100) NOT NULL,
  `postal_code` varchar(20) NOT NULL,
  `country` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `addresses_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Data for table `addresses` (CONTAINS PERSONAL ADDRESSES)
INSERT INTO `addresses` VALUES
(1, 1, 'home', '42 Baker Street', 'London', 'SW1A 1AA', 'United Kingdom'),
(2, 2, 'home', '15 Oxford Road', 'Manchester', 'M1 5QA', 'United Kingdom'),
(3, 3, 'home', '123 High Street', 'Birmingham', 'B1 2JP', 'United Kingdom');

-- Support tickets table with personal communications
CREATE TABLE `support_tickets` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `customer_id` int(11) NOT NULL,
  `subject` varchar(255) NOT NULL,
  `description` text NOT NULL,
  `agent_email` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `support_tickets_ibfk_1` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Support tickets with personal data
INSERT INTO `support_tickets` VALUES
(1, 1, 'Login Issues', 'I cannot access my account. My email is sarah.johnson@gmail.com. Please call me at +44 20 7946 0958 if needed.', 'support.agent@company.com'),
(2, 2, 'Billing Query', 'I have a question about my invoice. Please contact me at michael.chen@company.co.uk.', 'billing.support@company.com');

-- Stored procedure that processes personal data
DELIMITER $$
CREATE PROCEDURE `get_customer_details`(IN customer_email VARCHAR(255))
BEGIN
    SELECT c.*, a.street_address, a.city, a.postal_code, a.country
    FROM customers c
    LEFT JOIN addresses a ON c.id = a.customer_id
    WHERE c.email = customer_email;
END$$
DELIMITER ;

-- ⚠️  GDPR NOTICE: This export contains personal data including:
-- - Customer names, emails, phone numbers, dates of birth
-- - Home addresses and contact information
-- - Support communications and employee contact details

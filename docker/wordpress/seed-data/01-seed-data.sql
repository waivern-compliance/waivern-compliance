-- Waivern WordPress Test Data
-- This file contains realistic test data with PII patterns for testing the WordPress
USE wordpress;

-- Insert users with various roles
INSERT INTO
	wp_users (
		ID,
		user_login,
		user_pass,
		user_nicename,
		user_email,
		user_url,
		user_registered,
		user_activation_key,
		user_status,
		display_name
	)
VALUES
	(
		1,
		'admin',
		'$P$BZlPX7NIx8MYpXokBW2AGsN7i.aUOt0',
		'admin',
		'admin@testsite.com',
		'',
		'2024-01-01 00:00:00',
		'',
		0,
		'Site Administrator'
	),
	(
		2,
		'editor',
		'$P$BZlPX7NIx8MYpXokBW2AGsN7i.aUOt0',
		'editor',
		'editor@testsite.com',
		'',
		'2024-01-01 00:00:00',
		'',
		0,
		'Content Editor'
	),
	(
		3,
		'subscriber',
		'$P$BZlPX7NIx8MYpXokBW2AGsN7i.aUOt0',
		'subscriber',
		'subscriber@testsite.com',
		'',
		'2024-01-01 00:00:00',
		'',
		0,
		'John Subscriber'
	),
	(
		4,
		'johndoe',
		'$P$BZlPX7NIx8MYpXokBW2AGsN7i.aUOt0',
		'johndoe',
		'john.doe@example.com',
		'',
		'2024-01-02 00:00:00',
		'',
		0,
		'John Doe'
	);

-- Insert user metadata
INSERT INTO
	wp_usermeta (umeta_id, user_id, meta_key, meta_value)
VALUES
	(
		1,
		1,
		'wp_capabilities',
		'a:1:{s:13:"administrator";b:1;}'
	),
	(2, 1, 'wp_user_level', '10'),
	(3, 1, 'first_name', 'Admin'),
	(4, 1, 'last_name', 'User'),
	(5, 1, 'phone_number', '+1 (555) 123-4567'),
	(
		6,
		1,
		'billing_address',
		'123 Admin Street, Admin City, AC 12345'
	),
	(
		7,
		2,
		'wp_capabilities',
		'a:1:{s:6:"editor";b:1;}'
	),
	(8, 2, 'wp_user_level', '7'),
	(9, 2, 'first_name', 'Content'),
	(10, 2, 'last_name', 'Editor'),
	(11, 2, 'phone_number', '+44 20 7946 0958'),
	(
		12,
		3,
		'wp_capabilities',
		'a:1:{s:10:"subscriber";b:1;}'
	),
	(13, 3, 'wp_user_level', '0'),
	(14, 3, 'first_name', 'John'),
	(15, 3, 'last_name', 'Subscriber'),
	(
		16,
		4,
		'wp_capabilities',
		'a:1:{s:10:"subscriber";b:1;}'
	),
	(17, 4, 'wp_user_level', '0'),
	(18, 4, 'first_name', 'John'),
	(19, 4, 'last_name', 'Doe'),
	(20, 4, 'phone_number', '+1-800-555-0123'),
	(21, 4, 'ssn', '123-45-6789'),
	(22, 4, 'date_of_birth', '1985-03-15');

-- Insert posts with PII content
INSERT INTO
	wp_posts (
		ID,
		post_author,
		post_date,
		post_date_gmt,
		post_content,
		post_title,
		post_excerpt,
		post_status,
		comment_status,
		ping_status,
		post_password,
		post_name,
		to_ping,
		pinged,
		post_modified,
		post_modified_gmt,
		post_content_filtered,
		post_parent,
		guid,
		menu_order,
		post_type,
		post_mime_type,
		comment_count
	)
VALUES
	(
		1,
		1,
		'2024-01-01 12:00:00',
		'2024-01-01 12:00:00',
		'Welcome to our website! For support, please contact us at support@testsite.com or call us at +1 (555) 123-4567. Our office is located at 456 Business Ave, Suite 100, Business City, BC 54321.',
		'Welcome Post',
		'',
		'publish',
		'open',
		'open',
		'',
		'welcome-post',
		'',
		'',
		'2024-01-01 12:00:00',
		'2024-01-01 12:00:00',
		'',
		0,
		'http://localhost/welcome-post',
		0,
		'post',
		'',
		0
	),
	(
		2,
		2,
		'2024-01-02 10:00:00',
		'2024-01-02 10:00:00',
		'Customer testimonial: "I had an issue with my order and contacted customer service. Sarah Johnson (sarah.johnson@company.com) was incredibly helpful. You can reach her at extension 1234 or her direct line (555) 987-6543. My account number is ACC-789012 for reference." - Customer ID: CUST-456789',
		'Customer Testimonial',
		'',
		'publish',
		'open',
		'open',
		'',
		'customer-testimonial',
		'',
		'',
		'2024-01-02 10:00:00',
		'2024-01-02 10:00:00',
		'',
		0,
		'http://localhost/customer-testimonial',
		0,
		'post',
		'',
		0
	),
	(
		3,
		1,
		'2024-01-03 14:00:00',
		'2024-01-03 14:00:00',
		'Privacy Policy: We collect personal information including names, email addresses, phone numbers, and billing addresses. For EU residents, your GDPR rights include data portability. Contact our Data Protection Officer at dpo@testsite.com. For California residents under CCPA, you may request deletion of personal data by emailing privacy@testsite.com or calling 1-800-PRIVACY.',
		'Privacy Policy',
		'',
		'publish',
		'closed',
		'closed',
		'',
		'privacy-policy',
		'',
		'',
		'2024-01-03 14:00:00',
		'2024-01-03 14:00:00',
		'',
		0,
		'http://localhost/privacy-policy',
		0,
		'page',
		'',
		0
	),
	(
		4,
		2,
		'2024-01-04 16:00:00',
		'2024-01-04 16:00:00',
		'Employee Directory:
- Michael Smith, CEO: mike.smith@company.com, (555) 111-2222, SSN: 987-65-4321
- Jennifer Davis, CTO: j.davis@company.com, mobile: +1.555.333.4444
- Robert Wilson, HR Director: bob.wilson@company.com, home: 555-555-5555, DOB: 12/25/1975
Emergency contacts and personal information are stored in our HR system.',
		'Company Directory',
		'',
		'draft',
		'closed',
		'closed',
		'',
		'company-directory',
		'',
		'',
		'2024-01-04 16:00:00',
		'2024-01-04 16:00:00',
		'',
		0,
		'http://localhost/company-directory',
		0,
		'post',
		'',
		0
	),
	(
		5,
		3,
		'2024-01-05 09:00:00',
		'2024-01-05 09:00:00',
		'Contact form submission: Name: Alice Brown, Email: alice.brown@email.com, Phone: (555) 777-8888, Message: I need help with my account. My credit card ending in 4567 was charged incorrectly. Please call me at the number above or email me back.',
		'Contact Form Submission',
		'',
		'private',
		'closed',
		'closed',
		'',
		'contact-submission-001',
		'',
		'',
		'2024-01-05 09:00:00',
		'2024-01-05 09:00:00',
		'',
		0,
		'http://localhost/contact-submission-001',
		0,
		'post',
		'',
		0
	);

-- Insert post metadata with additional PII
INSERT INTO
	wp_postmeta (meta_id, post_id, meta_key, meta_value)
VALUES
	(1, 1, '_edit_last', '1'),
	(2, 1, 'customer_phone', '+1 (555) 123-4567'),
	(
		3,
		1,
		'business_address',
		'456 Business Ave, Suite 100, Business City, BC 54321'
	),
	(4, 2, '_edit_last', '2'),
	(5, 2, 'customer_id', 'CUST-456789'),
	(6, 2, 'account_number', 'ACC-789012'),
	(
		7,
		2,
		'support_agent_email',
		'sarah.johnson@company.com'
	),
	(8, 3, '_edit_last', '1'),
	(9, 3, 'dpo_email', 'dpo@testsite.com'),
	(10, 3, 'privacy_email', 'privacy@testsite.com'),
	(11, 4, '_edit_last', '2'),
	(12, 4, 'ceo_ssn', '987-65-4321'),
	(13, 4, 'hr_director_dob', '12/25/1975'),
	(14, 5, '_edit_last', '3'),
	(15, 5, 'submitter_email', 'alice.brown@email.com'),
	(16, 5, 'submitter_phone', '(555) 777-8888'),
	(17, 5, 'credit_card_last4', '4567');

-- Insert comments with PII
INSERT INTO
	wp_comments (
		comment_ID,
		comment_post_ID,
		comment_author,
		comment_author_email,
		comment_author_url,
		comment_author_IP,
		comment_date,
		comment_date_gmt,
		comment_content,
		comment_karma,
		comment_approved,
		comment_agent,
		comment_type,
		comment_parent,
		user_id
	)
VALUES
	(
		1,
		1,
		'Jane Customer',
		'jane.customer@email.com',
		'',
		'192.168.1.100',
		'2024-01-06 10:00:00',
		'2024-01-06 10:00:00',
		'Great service! I had an issue and called customer support at (555) 123-4567. The representative asked for my account number (ACC-999888) and resolved everything quickly. My email is jane.customer@email.com if you need to follow up.',
		0,
		'1',
		'Mozilla/5.0',
		'',
		0,
		0
	),
	(
		2,
		2,
		'Bob Reviewer',
		'bob.reviewer@domain.com',
		'',
		'10.0.0.5',
		'2024-01-07 15:30:00',
		'2024-01-07 15:30:00',
		'I can confirm this testimonial. I spoke with Sarah as well at her direct number (555) 987-6543. My case reference was CASE-112233. Highly recommend!',
		0,
		'1',
		'Chrome/120.0',
		'',
		1,
		0
	);

-- Insert comment metadata
INSERT INTO
	wp_commentmeta (meta_id, comment_id, meta_key, meta_value)
VALUES
	(1, 1, 'customer_phone', '(555) 123-4567'),
	(2, 1, 'account_number', 'ACC-999888'),
	(3, 2, 'case_reference', 'CASE-112233');

-- Insert options with site configuration
INSERT INTO
	wp_options (option_id, option_name, option_value, autoload)
VALUES
	(1, 'siteurl', 'http://localhost:8080', 'yes'),
	(2, 'home', 'http://localhost:8080', 'yes'),
	(3, 'blogname', 'Waivern Test Site', 'yes'),
	(
		4,
		'blogdescription',
		'WordPress test environment for PII detection',
		'yes'
	),
	(5, 'admin_email', 'admin@testsite.com', 'yes'),
	(6, 'start_of_week', '1', 'yes'),
	(7, 'use_balanceTags', '0', 'yes'),
	(8, 'use_smilies', '1', 'yes'),
	(9, 'require_name_email', '1', 'yes'),
	(10, 'comments_notify', '1', 'yes'),
	(11, 'posts_per_rss', '10', 'yes'),
	(12, 'rss_use_excerpt', '0', 'yes'),
	(13, 'mailserver_url', 'mail.example.com', 'yes'),
	(
		14,
		'mailserver_login',
		'login@example.com',
		'yes'
	),
	(15, 'mailserver_pass', 'password', 'yes'),
	(16, 'mailserver_port', '110', 'yes'),
	(17, 'default_category', '1', 'yes'),
	(18, 'default_comment_status', 'open', 'yes'),
	(19, 'default_ping_status', 'open', 'yes'),
	(20, 'default_pingback_flag', '0', 'yes'),
	(21, 'posts_per_page', '10', 'yes'),
	(22, 'date_format', 'F j, Y', 'yes'),
	(23, 'time_format', 'g:i a', 'yes'),
	(
		24,
		'links_updated_date_format',
		'F j, Y g:i a',
		'yes'
	),
	(25, 'comment_moderation', '0', 'yes'),
	(26, 'moderation_notify', '1', 'yes'),
	(27, 'permalink_structure', '/%postname%/', 'yes'),
	(28, 'rewrite_rules', '', 'yes'),
	(29, 'hack_file', '0', 'yes'),
	(30, 'blog_charset', 'UTF-8', 'yes'),
	(31, 'moderation_keys', '', 'no'),
	(32, 'active_analysers', 'a:0:{}', 'yes'),
	(33, 'category_base', '', 'yes'),
	(34, 'ping_sites', '', 'yes'),
	(35, 'comment_max_links', '2', 'yes'),
	(36, 'gmt_offset', '0', 'yes'),
	(37, 'default_email_category', '1', 'yes'),
	(38, 'recently_edited', '', 'no'),
	(39, 'template', 'twentytwentyfour', 'yes'),
	(40, 'stylesheet', 'twentytwentyfour', 'yes');

-- Create default category
INSERT INTO
	wp_terms (term_id, name, slug, term_group)
VALUES
	(1, 'Uncategorized', 'uncategorized', 0);

INSERT INTO
	wp_term_taxonomy (
		term_taxonomy_id,
		term_id,
		taxonomy,
		description,
		parent,
		count
	)
VALUES
	(1, 1, 'category', '', 0, 5);

-- Link posts to categories
INSERT INTO
	wp_term_relationships (object_id, term_taxonomy_id, term_order)
VALUES
	(1, 1, 0),
	(2, 1, 0),
	(4, 1, 0),
	(5, 1, 0);

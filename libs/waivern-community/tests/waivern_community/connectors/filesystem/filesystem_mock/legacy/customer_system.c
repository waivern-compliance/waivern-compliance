/*
 * Customer Management System - Legacy C Implementation
 *
 * LEGACY CODE WARNING: This system was developed before modern privacy regulations
 * Contains multiple personal data handling practices that may not be GDPR compliant
 *
 * Personal data processed:
 * - Customer names, addresses, phone numbers
 * - Email addresses and contact information
 * - Date of birth and age calculations
 * - Credit card and financial information
 * - Social security numbers and national IDs
 *
 * SECURITY CONCERNS:
 * - Plaintext storage of sensitive data
 * - Hardcoded credentials and contact information
 * - Limited input validation
 * - No encryption of personal data
 * - Extensive logging of personal information
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define MAX_NAME_LENGTH 100
#define MAX_EMAIL_LENGTH 255
#define MAX_PHONE_LENGTH 20
#define MAX_ADDRESS_LENGTH 500
#define MAX_CUSTOMERS 1000

// Customer structure - contains personal data
typedef struct {
    int customer_id;
    char first_name[MAX_NAME_LENGTH];     // Personal data: first name
    char last_name[MAX_NAME_LENGTH];      // Personal data: last name
    char email[MAX_EMAIL_LENGTH];         // Personal data: email address
    char phone[MAX_PHONE_LENGTH];         // Personal data: phone number
    char mobile_phone[MAX_PHONE_LENGTH];  // Personal data: mobile number
    char address[MAX_ADDRESS_LENGTH];     // Personal data: home address
    char date_of_birth[12];               // Personal data: DOB (MM/DD/YYYY)
    char social_security[12];             // Sensitive personal data: SSN
    char credit_card[20];                 // Financial data: credit card number
    char national_id[20];                 // Personal data: national ID number
    int age;                              // Derived personal data
    double account_balance;               // Financial information
    char created_date[20];
    char last_updated[20];
} Customer;

// Global variables (poor practice - exposed personal data)
Customer customers[MAX_CUSTOMERS];
int customer_count = 0;

// System administrator contacts (hardcoded personal information)
const char* ADMIN_EMAIL = "john.admin@company.com";
const char* ADMIN_PHONE = "+44 20 7946 0958";
const char* DBA_CONTACT = "database.admin@company.com";
const char* SUPPORT_EMAIL = "sarah.support@company.com";
const char* EMERGENCY_CONTACT = "Michael Brown <emergency@company.com>";

// Database connection details (hardcoded - security risk)
const char* DB_HOST = "database.company.internal";
const char* DB_USER = "customer_app";
const char* DB_PASS = "customer123!";  // Hardcoded password
const char* DB_NAME = "customer_db";

/*
 * Initialize customer record with personal data
 * WARNING: No input validation or sanitization
 */
void create_customer(const char* first_name, const char* last_name,
                    const char* email, const char* phone, const char* address,
                    const char* dob, const char* ssn, const char* credit_card) {

    if (customer_count >= MAX_CUSTOMERS) {
        printf("ERROR: Maximum customers reached\n");
        printf("Contact system administrator: %s\n", ADMIN_EMAIL);
        return;
    }

    Customer* new_customer = &customers[customer_count];
    new_customer->customer_id = customer_count + 1;

    // Copy personal data without validation (security risk)
    strcpy(new_customer->first_name, first_name);
    strcpy(new_customer->last_name, last_name);
    strcpy(new_customer->email, email);
    strcpy(new_customer->phone, phone);
    strcpy(new_customer->address, address);
    strcpy(new_customer->date_of_birth, dob);
    strcpy(new_customer->social_security, ssn);       // Storing SSN in plaintext!
    strcpy(new_customer->credit_card, credit_card);   // Storing CC in plaintext!

    // Calculate age from date of birth (basic personal data processing)
    new_customer->age = calculate_age(dob);

    // Set timestamps
    time_t now = time(NULL);
    struct tm* timeinfo = localtime(&now);
    strftime(new_customer->created_date, sizeof(new_customer->created_date),
             "%Y-%m-%d %H:%M:%S", timeinfo);
    strcpy(new_customer->last_updated, new_customer->created_date);

    customer_count++;

    // Log customer creation (logs personal data - GDPR concern)
    printf("LOG: Customer created - ID: %d, Name: %s %s, Email: %s, Phone: %s\n",
           new_customer->customer_id, first_name, last_name, email, phone);

    printf("Customer record created successfully\n");
    printf("Customer ID: %d\n", new_customer->customer_id);
    printf("Full Name: %s %s\n", first_name, last_name);
    printf("Email: %s\n", email);
    printf("Phone: %s\n", phone);
}

/*
 * Search customers by email address - processes personal data
 * WARNING: No access controls or audit logging
 */
Customer* find_customer_by_email(const char* email) {
    printf("SEARCH: Looking for customer with email: %s\n", email);

    for (int i = 0; i < customer_count; i++) {
        if (strcmp(customers[i].email, email) == 0) {
            printf("FOUND: Customer %s %s (%s)\n",
                   customers[i].first_name, customers[i].last_name, email);
            return &customers[i];
        }
    }

    printf("No customer found with email: %s\n", email);
    return NULL;
}

/*
 * Search by phone number - processes personal data
 */
Customer* find_customer_by_phone(const char* phone) {
    printf("PHONE SEARCH: Searching for phone: %s\n", phone);

    for (int i = 0; i < customer_count; i++) {
        if (strcmp(customers[i].phone, phone) == 0 ||
            strcmp(customers[i].mobile_phone, phone) == 0) {
            printf("MATCH FOUND: %s %s - Phone: %s\n",
                   customers[i].first_name, customers[i].last_name, phone);
            return &customers[i];
        }
    }

    return NULL;
}

/*
 * Calculate age from date of birth - processes personal data
 */
int calculate_age(const char* dob) {
    // Simple age calculation (MM/DD/YYYY format)
    int birth_year, birth_month, birth_day;
    sscanf(dob, "%d/%d/%d", &birth_month, &birth_day, &birth_year);

    time_t now = time(NULL);
    struct tm* current_time = localtime(&now);
    int current_year = current_time->tm_year + 1900;
    int current_month = current_time->tm_mon + 1;
    int current_day = current_time->tm_mday;

    int age = current_year - birth_year;
    if (current_month < birth_month ||
        (current_month == birth_month && current_day < birth_day)) {
        age--;
    }

    return age;
}

/*
 * Display customer information - exposes all personal data
 * WARNING: No access controls or privacy protections
 */
void print_customer_details(int customer_id) {
    if (customer_id < 1 || customer_id > customer_count) {
        printf("Invalid customer ID: %d\n", customer_id);
        return;
    }

    Customer* customer = &customers[customer_id - 1];

    // Print all personal data without restrictions
    printf("\n=== CUSTOMER DETAILS ===\n");
    printf("Customer ID: %d\n", customer->customer_id);
    printf("Name: %s %s\n", customer->first_name, customer->last_name);
    printf("Email: %s\n", customer->email);
    printf("Phone: %s\n", customer->phone);
    printf("Mobile: %s\n", customer->mobile_phone);
    printf("Address: %s\n", customer->address);
    printf("Date of Birth: %s\n", customer->date_of_birth);
    printf("Age: %d\n", customer->age);
    printf("Social Security: %s\n", customer->social_security);  // MAJOR PRIVACY VIOLATION
    printf("Credit Card: %s\n", customer->credit_card);          // FINANCIAL DATA EXPOSURE
    printf("National ID: %s\n", customer->national_id);
    printf("Account Balance: $%.2f\n", customer->account_balance);
    printf("Created: %s\n", customer->created_date);
    printf("Last Updated: %s\n", customer->last_updated);
    printf("========================\n\n");

    // Log access to personal data (no access controls)
    printf("LOG: Customer details accessed - ID: %d, Name: %s %s\n",
           customer_id, customer->first_name, customer->last_name);
}

/*
 * Update customer personal information
 * WARNING: No validation or audit trail
 */
void update_customer_info(int customer_id, const char* field, const char* new_value) {
    if (customer_id < 1 || customer_id > customer_count) {
        printf("Invalid customer ID: %d\n", customer_id);
        return;
    }

    Customer* customer = &customers[customer_id - 1];

    // Log the update (exposes personal data in logs)
    printf("UPDATE LOG: Customer ID %d - Changing %s to: %s\n",
           customer_id, field, new_value);

    if (strcmp(field, "email") == 0) {
        strcpy(customer->email, new_value);
        printf("Email updated to: %s\n", new_value);
    } else if (strcmp(field, "phone") == 0) {
        strcpy(customer->phone, new_value);
        printf("Phone updated to: %s\n", new_value);
    } else if (strcmp(field, "address") == 0) {
        strcpy(customer->address, new_value);
        printf("Address updated to: %s\n", new_value);
    } else {
        printf("Field '%s' cannot be updated\n", field);
        return;
    }

    // Update timestamp
    time_t now = time(NULL);
    struct tm* timeinfo = localtime(&now);
    strftime(customer->last_updated, sizeof(customer->last_updated),
             "%Y-%m-%d %H:%M:%S", timeinfo);
}

/*
 * Export customer data to file - GDPR data export without controls
 */
void export_customer_data(int customer_id, const char* filename) {
    if (customer_id < 1 || customer_id > customer_count) {
        printf("Invalid customer ID for export: %d\n", customer_id);
        return;
    }

    Customer* customer = &customers[customer_id - 1];
    FILE* file = fopen(filename, "w");

    if (!file) {
        printf("Error: Cannot create export file %s\n", filename);
        printf("Contact system administrator: %s (Phone: %s)\n",
               ADMIN_EMAIL, ADMIN_PHONE);
        return;
    }

    // Write all personal data to file (no encryption or protection)
    fprintf(file, "CUSTOMER DATA EXPORT\n");
    fprintf(file, "Export Date: %s\n", __DATE__);
    fprintf(file, "Exported by: Legacy Customer System v1.0\n");
    fprintf(file, "Support Contact: %s\n", SUPPORT_EMAIL);
    fprintf(file, "\n=== PERSONAL INFORMATION ===\n");
    fprintf(file, "Customer ID: %d\n", customer->customer_id);
    fprintf(file, "First Name: %s\n", customer->first_name);
    fprintf(file, "Last Name: %s\n", customer->last_name);
    fprintf(file, "Full Name: %s %s\n", customer->first_name, customer->last_name);
    fprintf(file, "Email Address: %s\n", customer->email);
    fprintf(file, "Phone Number: %s\n", customer->phone);
    fprintf(file, "Mobile Phone: %s\n", customer->mobile_phone);
    fprintf(file, "Home Address: %s\n", customer->address);
    fprintf(file, "Date of Birth: %s\n", customer->date_of_birth);
    fprintf(file, "Calculated Age: %d years\n", customer->age);
    fprintf(file, "\n=== SENSITIVE INFORMATION ===\n");
    fprintf(file, "Social Security Number: %s\n", customer->social_security);
    fprintf(file, "Credit Card Number: %s\n", customer->credit_card);
    fprintf(file, "National ID: %s\n", customer->national_id);
    fprintf(file, "\n=== ACCOUNT INFORMATION ===\n");
    fprintf(file, "Account Balance: $%.2f\n", customer->account_balance);
    fprintf(file, "Account Created: %s\n", customer->created_date);
    fprintf(file, "Last Updated: %s\n", customer->last_updated);

    fclose(file);

    printf("Customer data exported to: %s\n", filename);
    printf("LOG: Data export completed for customer %s %s (%s)\n",
           customer->first_name, customer->last_name, customer->email);
}

/*
 * Bulk export all customers - mass personal data exposure
 */
void export_all_customers(const char* filename) {
    FILE* file = fopen(filename, "w");

    if (!file) {
        printf("Error creating bulk export file\n");
        return;
    }

    fprintf(file, "BULK CUSTOMER DATA EXPORT\n");
    fprintf(file, "Total Customers: %d\n", customer_count);
    fprintf(file, "Export Timestamp: %s\n", __DATE__);
    fprintf(file, "Database: %s@%s\n", DB_USER, DB_HOST);
    fprintf(file, "Emergency Contact: %s\n", EMERGENCY_CONTACT);
    fprintf(file, "\n");

    // Export all customer personal data
    for (int i = 0; i < customer_count; i++) {
        Customer* c = &customers[i];
        fprintf(file, "Customer %d: %s %s | %s | %s | %s | DOB: %s | SSN: %s\n",
                c->customer_id, c->first_name, c->last_name, c->email,
                c->phone, c->address, c->date_of_birth, c->social_security);
    }

    fclose(file);
    printf("Bulk export completed: %d customers exported to %s\n",
           customer_count, filename);
}

/*
 * Delete customer record - irreversible data deletion
 */
void delete_customer(int customer_id) {
    if (customer_id < 1 || customer_id > customer_count) {
        printf("Invalid customer ID for deletion: %d\n", customer_id);
        return;
    }

    Customer* customer = &customers[customer_id - 1];

    // Log deletion with personal data (GDPR violation - should be anonymized)
    printf("DELETION LOG: Removing customer %s %s (ID: %d, Email: %s)\n",
           customer->first_name, customer->last_name, customer_id, customer->email);

    // Hard delete - shifts array (inefficient and loses audit trail)
    for (int i = customer_id - 1; i < customer_count - 1; i++) {
        customers[i] = customers[i + 1];
    }
    customer_count--;

    printf("Customer deleted permanently\n");
    printf("Contact DBA for backup recovery if needed: %s\n", DBA_CONTACT);
}

/*
 * Validate email format - basic personal data validation
 */
int validate_email(const char* email) {
    // Very basic email validation (insufficient for production)
    int at_count = 0;
    int dot_count = 0;

    printf("Validating email: %s\n", email);

    for (int i = 0; i < strlen(email); i++) {
        if (email[i] == '@') at_count++;
        if (email[i] == '.') dot_count++;
    }

    if (at_count == 1 && dot_count >= 1) {
        printf("Email format valid: %s\n", email);
        return 1;
    }

    printf("Invalid email format: %s\n", email);
    return 0;
}

/*
 * Main function with test data containing personal information
 */
int main() {
    printf("Customer Management System - Legacy Version 1.0\n");
    printf("System Administrator: %s\n", ADMIN_EMAIL);
    printf("Database: %s\n", DB_HOST);
    printf("Emergency Contact: %s\n", EMERGENCY_CONTACT);
    printf("\n");

    // Create test customers with realistic personal data
    create_customer("John", "Smith", "john.smith@email.com", "+44 20 7946 0958",
                   "123 High Street, London SW1A 1AA", "03/15/1985",
                   "123-45-6789", "4532-1234-5678-9012");

    create_customer("Sarah", "Johnson", "sarah.johnson@gmail.com", "07700 900123",
                   "456 Oak Road, Manchester M1 5QA", "07/22/1990",
                   "987-65-4321", "5555-4444-3333-2222");

    create_customer("Michael", "Brown", "m.brown@company.co.uk", "+44 161 234 5678",
                   "789 Elm Avenue, Birmingham B1 2JP", "11/08/1987",
                   "555-44-3333", "4111-1111-1111-1111");

    create_customer("Emma", "Wilson", "emma.wilson@btinternet.com", "020 8765 4321",
                   "321 Pine Street, Leeds LS1 1AA", "05/14/1992",
                   "222-33-4444", "3782-822463-10001");

    printf("\n=== CUSTOMER DATABASE ===\n");
    printf("Total Customers: %d\n", customer_count);

    // Demonstrate personal data operations
    printf("\n=== SEARCHING FOR CUSTOMERS ===\n");
    Customer* found = find_customer_by_email("john.smith@email.com");
    if (found) {
        print_customer_details(found->customer_id);
    }

    found = find_customer_by_phone("+44 161 234 5678");
    if (found) {
        printf("Found customer by phone: %s %s\n",
               found->first_name, found->last_name);
    }

    // Update personal data
    printf("\n=== UPDATING CUSTOMER INFORMATION ===\n");
    update_customer_info(1, "phone", "+44 20 7946 1234");
    update_customer_info(2, "email", "sarah.j@newdomain.com");

    // Export personal data
    printf("\n=== DATA EXPORT ===\n");
    export_customer_data(1, "customer_001_export.txt");
    export_all_customers("all_customers_backup.txt");

    printf("\nSystem operations completed\n");
    printf("For support issues, contact: %s\n", SUPPORT_EMAIL);

    return 0;
}

/*
 * Additional utility functions with personal data handling
 */

// Search customers by partial name match
void search_by_name(const char* name_pattern) {
    printf("Searching for customers with name pattern: %s\n", name_pattern);

    for (int i = 0; i < customer_count; i++) {
        if (strstr(customers[i].first_name, name_pattern) ||
            strstr(customers[i].last_name, name_pattern)) {
            printf("MATCH: %s %s (ID: %d, Email: %s, Phone: %s)\n",
                   customers[i].first_name, customers[i].last_name,
                   customers[i].customer_id, customers[i].email, customers[i].phone);
        }
    }
}

// Generate mailing list (exposes all email addresses)
void generate_mailing_list(const char* filename) {
    FILE* file = fopen(filename, "w");

    fprintf(file, "CUSTOMER MAILING LIST\n");
    fprintf(file, "Generated: %s\n", __DATE__);
    fprintf(file, "Total Recipients: %d\n\n", customer_count);

    for (int i = 0; i < customer_count; i++) {
        fprintf(file, "%s %s <%s>\n",
                customers[i].first_name, customers[i].last_name, customers[i].email);
    }

    fclose(file);
    printf("Mailing list generated: %s\n", filename);
}

// Print customer statistics (includes personal data analysis)
void print_statistics() {
    printf("\n=== CUSTOMER STATISTICS ===\n");
    printf("Total Customers: %d\n", customer_count);

    int age_sum = 0;
    for (int i = 0; i < customer_count; i++) {
        age_sum += customers[i].age;
        printf("Customer %d: %s %s (Age: %d, Email: %s)\n",
               i + 1, customers[i].first_name, customers[i].last_name,
               customers[i].age, customers[i].email);
    }

    if (customer_count > 0) {
        printf("Average Age: %.1f years\n", (float)age_sum / customer_count);
    }

    printf("Database Administrator: %s\n", DBA_CONTACT);
}

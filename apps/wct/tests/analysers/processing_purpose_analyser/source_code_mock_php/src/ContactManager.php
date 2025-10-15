<?php

class ContactManager
{
    public function saveContact($first_name, $last_name, $email_address, $phone_number, $company)
    {
        $sql = "INSERT INTO contacts (first_name, last_name, email, phone, company, created_at) VALUES (?, ?, ?, ?, ?, NOW())";
        return $this->executeQuery($sql, [$first_name, $last_name, $email_address, $phone_number, $company]);
    }

    public function getContactByEmail($email_address)
    {
        $sql = "SELECT first_name, last_name, email, phone, company FROM contacts WHERE email = ?";
        return $this->executeQuery($sql, [$email_address]);
    }

    public function updateContactInfo($contact_id, $first_name, $last_name, $phone_number)
    {
        $sql = "UPDATE contacts SET first_name = ?, last_name = ?, phone = ? WHERE id = ?";
        return $this->executeQuery($sql, [$first_name, $last_name, $phone_number, $contact_id]);
    }

    public function searchContacts($search_term)
    {
        $sql = "SELECT * FROM contacts WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ?";
        $search_pattern = "%$search_term%";
        return $this->executeQuery($sql, [$search_pattern, $search_pattern, $search_pattern]);
    }

    public function exportContactsToCSV()
    {
        $sql = "SELECT first_name, last_name, email, phone, company FROM contacts";
        $contacts = $this->executeQuery($sql, []);

        $csv_data = "First Name,Last Name,Email,Phone,Company\n";
        foreach ($contacts as $contact) {
            $csv_data .= implode(',', $contact) . "\n";
        }

        return $csv_data;
    }

    private function executeQuery($sql, $params)
    {
        // Database query execution logic
        return [];
    }
}

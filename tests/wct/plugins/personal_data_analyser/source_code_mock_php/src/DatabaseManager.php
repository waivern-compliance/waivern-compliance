<?php

class DatabaseManager
{
    private $connection;

    public function __construct($host, $username, $password, $database)
    {
        $this->connection = new PDO("mysql:host=$host;dbname=$database", $username, $password);
    }

    public function getUserData($user_id)
    {
        $sql = "SELECT u.email, u.first_name, u.last_name, p.phone, a.address
                FROM users u
                LEFT JOIN profiles p ON u.id = p.user_id
                LEFT JOIN addresses a ON u.id = a.user_id
                WHERE u.id = ?";
        return $this->executeQuery($sql, [$user_id]);
    }

    public function searchUsersByEmail($email_pattern)
    {
        $sql = "SELECT * FROM users WHERE email LIKE ?";
        return $this->executeQuery($sql, ["%$email_pattern%"]);
    }

    public function getUserPayments($user_id)
    {
        $sql = "SELECT p.amount, p.credit_card_last4, p.created_at
                FROM payments p
                WHERE p.customer_id = ?";
        return $this->executeQuery($sql, [$user_id]);
    }

    public function deleteUserData($user_id)
    {
        $queries = [
            "DELETE FROM profiles WHERE user_id = ?",
            "DELETE FROM addresses WHERE user_id = ?",
            "DELETE FROM payments WHERE customer_id = ?",
            "DELETE FROM users WHERE id = ?"
        ];

        foreach ($queries as $sql) {
            $this->executeQuery($sql, [$user_id]);
        }
    }

    private function executeQuery($sql, $params)
    {
        $stmt = $this->connection->prepare($sql);
        $stmt->execute($params);
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
}

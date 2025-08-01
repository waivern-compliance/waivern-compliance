<?php

class Database
{
    private static $instance = null;
    private $connection;

    private function __construct()
    {
        $host = $_ENV['DB_HOST'] ?? 'localhost';
        $username = $_ENV['DB_USER'] ?? 'root';
        $password = $_ENV['DB_PASSWORD'] ?? '';
        $database = $_ENV['DB_NAME'] ?? 'app_database';

        $this->connection = new PDO("mysql:host=$host;dbname=$database", $username, $password);
    }

    public static function getInstance()
    {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    public function getUserByEmail($email_address)
    {
        $sql = "SELECT id, email, first_name, last_name, phone, created_at FROM users WHERE email = ?";
        $stmt = $this->connection->prepare($sql);
        $stmt->execute([$email_address]);
        return $stmt->fetch(PDO::FETCH_ASSOC);
    }

    public function createUser($email, $password_hash, $first_name, $last_name, $phone)
    {
        $sql = "INSERT INTO users (email, password, first_name, last_name, phone, created_at) VALUES (?, ?, ?, ?, ?, NOW())";
        $stmt = $this->connection->prepare($sql);
        return $stmt->execute([$email, $password_hash, $first_name, $last_name, $phone]);
    }

    public function updateUserProfile($user_id, $first_name, $last_name, $phone, $address)
    {
        $sql = "UPDATE users SET first_name = ?, last_name = ?, phone = ?, address = ? WHERE id = ?";
        $stmt = $this->connection->prepare($sql);
        return $stmt->execute([$first_name, $last_name, $phone, $address, $user_id]);
    }

    public function logUserActivity($user_id, $activity, $ip_address, $user_agent)
    {
        $sql = "INSERT INTO user_activity (user_id, activity, ip_address, user_agent, timestamp) VALUES (?, ?, ?, ?, NOW())";
        $stmt = $this->connection->prepare($sql);
        return $stmt->execute([$user_id, $activity, $ip_address, $user_agent]);
    }
}

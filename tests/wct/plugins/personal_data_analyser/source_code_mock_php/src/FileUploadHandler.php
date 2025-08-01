<?php

class FileUploadHandler
{
    private $upload_directory = '/uploads/';

    public function uploadUserAvatar($user_id, $file_data, $user_email)
    {
        $filename = $user_id . '_avatar_' . time() . '.jpg';
        $filepath = $this->upload_directory . $filename;

        if (move_uploaded_file($file_data['tmp_name'], $filepath)) {
            $this->logFileUpload($user_id, $filename, $user_email);
            return $filepath;
        }

        return false;
    }

    public function uploadDocuments($user_id, $files, $document_type)
    {
        $uploaded_files = [];

        foreach ($files as $file) {
            if ($this->validateFile($file)) {
                $filename = $user_id . '_' . $document_type . '_' . time() . '.pdf';
                $filepath = $this->upload_directory . $filename;

                if (move_uploaded_file($file['tmp_name'], $filepath)) {
                    $uploaded_files[] = $filepath;
                }
            }
        }

        return $uploaded_files;
    }

    public function getUserFiles($user_id)
    {
        $sql = "SELECT filename, upload_date, file_type FROM file_uploads WHERE user_id = ?";
        return $this->executeQuery($sql, [$user_id]);
    }

    private function validateFile($file)
    {
        $allowed_types = ['image/jpeg', 'image/png', 'application/pdf'];
        return in_array($file['type'], $allowed_types) && $file['size'] <= 5000000;
    }

    private function logFileUpload($user_id, $filename, $user_email)
    {
        $sql = "INSERT INTO file_uploads (user_id, filename, user_email, upload_date) VALUES (?, ?, ?, NOW())";
        $this->executeQuery($sql, [$user_id, $filename, $user_email]);
    }

    private function executeQuery($sql, $params)
    {
        // Database query execution logic
        return [];
    }
}

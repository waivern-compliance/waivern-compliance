<?php

class Profile
{
    private $profile_id;
    private $username;
    private $bio;
    private $avatar_url;
    private $location;
    private $birth_date;

    public function createProfile($username, $bio, $location)
    {
        $this->username = $username;
        $this->bio = $bio;
        $this->location = $location;
    }

    public function updatePersonalInfo($birth_date, $location)
    {
        $this->birth_date = $birth_date;
        $this->location = $location;
    }

    public function getProfileData()
    {
        return [
            'username' => $this->username,
            'bio' => $this->bio,
            'location' => $this->location
        ];
    }
}

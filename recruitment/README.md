# Recruitment Module

## Purpose

The Recruitment Module is designed to manage the end-to-end hiring process within the application. It allows users to track job openings, manage candidate applications, schedule interviews, and follow candidate progress through various stages of recruitment.

## Database Schema Overview

The module introduces the following new tables to the database:

*   **`JobOpenings`**: Stores information about job vacancies, including title, description, status (e.g., Open, Closed), department, and closing dates.
*   **`Candidates`**: Contains details of individuals applying for jobs, such as their name, contact information, resume/cover letter paths, application source, and current application status. Each candidate is linked to a specific job opening.
*   **`RecruitmentSteps`**: Defines the customizable stages for each job opening's hiring process (e.g., 'Application Review', 'Phone Screen', 'Technical Interview').
*   **`CandidateProgress`**: Tracks the status of a candidate at each recruitment step for a particular job opening.
*   **`Interviews`**: Manages interview schedules, including candidate, job opening, interviewer, time, type (phone, video, on-site), status, and feedback.

Appropriate status types (e.g., 'JobOpening', 'CandidateApplication', 'InterviewStatus') have been added to the `StatusSettings` table to support these entities.

## API Endpoints

The module exposes its functionalities via RESTful API endpoints under the main prefix `/recruitment`. Key resources include:

*   **Job Openings:**
    *   `GET /recruitment/job-openings/`: List all job openings.
    *   `POST /recruitment/job-openings/`: Create a new job opening.
    *   `GET /recruitment/job-openings/{job_opening_id}`: Get details of a specific job opening.
    *   `PUT /recruitment/job-openings/{job_opening_id}`: Update a job opening.
    *   `DELETE /recruitment/job-openings/{job_opening_id}`: Delete a job opening.
    *   `GET /recruitment/job-openings/{job_opening_id}/candidates/`: List candidates for a specific job opening.
*   **Candidates:**
    *   `GET /recruitment/candidates/`: List all candidates (supports filtering).
    *   `POST /recruitment/candidates/`: Add a new candidate.
    *   `GET /recruitment/candidates/{candidate_id}`: Get details of a specific candidate.
    *   `PUT /recruitment/candidates/{candidate_id}`: Update a candidate.
    *   `DELETE /recruitment/candidates/{candidate_id}`: Delete a candidate.
*   **Interviews:**
    *   `GET /recruitment/interviews/`: List all interviews (supports filtering).
    *   `POST /recruitment/interviews/`: Schedule a new interview.
    *   `GET /recruitment/interviews/{interview_id}`: Get details of a specific interview.
    *   `PUT /recruitment/interviews/{interview_id}`: Update an interview.
    *   `DELETE /recruitment/interviews/{interview_id}`: Delete an interview.
*   **Recruitment Steps:**
    *   `GET /recruitment/job-openings/{job_opening_id}/steps`: List steps for a job.
    *   `POST /recruitment/job-openings/{job_opening_id}/steps`: Add a recruitment step to a job.
    *   `GET /recruitment/steps/{recruitment_step_id}`: Get details of a specific step.
    *   `PUT /recruitment/steps/{recruitment_step_id}`: Update a step.
    *   `DELETE /recruitment/steps/{recruitment_step_id}`: Delete a step.
*   **Candidate Progress:**
    *   `GET /recruitment/candidates/{candidate_id}/progress`: List all progress entries for a candidate.
    *   `POST /recruitment/candidate-progress/`: Create a new candidate progress entry.
    *   `GET /recruitment/candidate-progress/{candidate_progress_id}`: Get a specific progress entry.
    *   `PUT /recruitment/candidate-progress/{candidate_progress_id}`: Update a progress entry.
    *   `DELETE /recruitment/candidate-progress/{candidate_progress_id}`: Delete a progress entry.

Pydantic models are used for request and response validation.

## User Interface

The Recruitment Module is accessible via the "Modules" menu in the main application. It provides the following tabs:

*   **Job Openings:**
    *   Displays a list of all job openings.
    *   Allows adding, editing, and deleting job openings.
    *   Provides functionality to view candidates associated with a selected job opening.
*   **Candidates:**
    *   Displays a list of candidates.
    *   Can be filtered by job opening.
    *   Allows adding new candidates, viewing/editing their details (including resume path as text input), and deleting candidates.
*   **Interviews:**
    *   Displays a list of scheduled interviews.
    *   Can be filtered by job opening and candidate.
    *   Allows scheduling new interviews, viewing/editing interview details (including feedback), and canceling interviews.

## Future Enhancements (Considerations)

*   Dynamic loading of statuses in dialogs from `StatusSettings`.
*   File upload/management for resumes and cover letters.
*   Dedicated UI for managing `RecruitmentSteps` per job opening.
*   Visual workflow for `CandidateProgress`.
*   Notifications for interview scheduling, status changes, etc.
*   More comprehensive unit and UI testing (once environment issues are resolved).
```

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, date

# CRUD function imports
from db.cruds import (
    recruitment_job_openings_crud,
    recruitment_candidates_crud,
    recruitment_interviews_crud,
    recruitment_steps_crud,
    recruitment_candidate_progress_crud
)

# Main router for the entire recruitment module
router = APIRouter(prefix="/recruitment", tags=["Recruitment - Main"])

# --- Pydantic Models for Job Openings ---

class JobOpeningBase(BaseModel):
    title: str = Field(..., description="Title of the job opening.")
    description: Optional[str] = Field(None, description="Detailed description of the job.")
    status_id: Optional[int] = Field(None, description="Status ID from StatusSettings (e.g., Open, Closed).")
    department_id: Optional[int] = Field(None, description="Department ID (if applicable).")
    # created_by_user_id will likely be set based on authenticated user in a real app
    created_by_user_id: Optional[str] = Field(None, description="User ID of the creator.")
    closing_date: Optional[date] = Field(None, description="Date when the job opening closes.")

class JobOpeningCreate(JobOpeningBase):
    pass

class JobOpeningUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status_id: Optional[int] = None
    department_id: Optional[int] = None
    closing_date: Optional[date] = None

class JobOpeningResponse(JobOpeningBase):
    job_opening_id: str = Field(..., description="Unique ID of the job opening.")
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True # For compatibility with ORM-like objects (dicts in our case)

# --- API Router for Job Openings ---
router_job_openings = APIRouter(tags=["Recruitment - Job Openings"])

@router_job_openings.post("/", response_model=JobOpeningResponse, status_code=201)
async def create_job_opening(job_opening: JobOpeningCreate = Body(...)):
    """
    Create a new job opening.
    """
    job_opening_data = job_opening.dict(exclude_unset=True)
    # In a real app, created_by_user_id would be derived from the authenticated user session.
    # For now, it's passed or None.

    new_job_opening_id = recruitment_job_openings_crud.add_job_opening(job_opening_data)
    if not new_job_opening_id:
        raise HTTPException(status_code=500, detail="Failed to create job opening.")

    created_job_opening = recruitment_job_openings_crud.get_job_opening_by_id(new_job_opening_id)
    if not created_job_opening:
        raise HTTPException(status_code=500, detail="Job opening created but failed to retrieve.")
    return created_job_opening

@router_job_openings.get("/{job_opening_id}", response_model=JobOpeningResponse)
async def get_job_opening(job_opening_id: str):
    """
    Get a specific job opening by its ID.
    """
    job_opening = recruitment_job_openings_crud.get_job_opening_by_id(job_opening_id)
    if not job_opening:
        raise HTTPException(status_code=404, detail="Job opening not found.")
    return job_opening

@router_job_openings.get("/", response_model=List[JobOpeningResponse])
async def list_job_openings(
    status_id: Optional[int] = Query(None, description="Filter by status ID."),
    department_id: Optional[int] = Query(None, description="Filter by department ID."),
    limit: int = Query(100, ge=1, le=500, description="Number of job openings to return."),
    offset: int = Query(0, ge=0, description="Offset for pagination.")
):
    """
    List all job openings with optional filters and pagination.
    """
    filters = {}
    if status_id is not None:
        filters['status_id'] = status_id
    if department_id is not None:
        filters['department_id'] = department_id

    job_openings = recruitment_job_openings_crud.get_all_job_openings(filters=filters, limit=limit, offset=offset)
    return job_openings

@router_job_openings.put("/{job_opening_id}", response_model=JobOpeningResponse)
async def update_job_opening_details(job_opening_id: str, job_opening_update: JobOpeningUpdate = Body(...)):
    """
    Update an existing job opening.
    """
    update_data = job_opening_update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided.")

    success = recruitment_job_openings_crud.update_job_opening(job_opening_id, update_data)
    if not success:
        # Check if the job opening even exists before saying update failed vs not found
        existing_opening = recruitment_job_openings_crud.get_job_opening_by_id(job_opening_id)
        if not existing_opening:
            raise HTTPException(status_code=404, detail="Job opening not found.")
        raise HTTPException(status_code=500, detail="Failed to update job opening.")

    updated_job_opening = recruitment_job_openings_crud.get_job_opening_by_id(job_opening_id)
    if not updated_job_opening:
         raise HTTPException(status_code=404, detail="Job opening updated but failed to retrieve.") # Should not happen if update was successful
    return updated_job_opening

@router_job_openings.delete("/{job_opening_id}", status_code=204)
async def delete_single_job_opening(job_opening_id: str):
    """
    Delete a specific job opening by its ID.
    """
    existing_opening = recruitment_job_openings_crud.get_job_opening_by_id(job_opening_id)
    if not existing_opening:
        raise HTTPException(status_code=404, detail="Job opening not found.")

    success = recruitment_job_openings_crud.delete_job_opening(job_opening_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete job opening.")
    return None # FastAPI will return 204 No Content

# Include Job Openings router into the main recruitment router
router.include_router(router_job_openings, prefix="/job-openings")


# --- Pydantic Models for Candidates ---

class CandidateBase(BaseModel):
    job_opening_id: str = Field(..., description="ID of the job opening this candidate applied for.")
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    resume_path: Optional[str] = Field(None, description="Path to the stored resume file.")
    cover_letter_path: Optional[str] = Field(None, description="Path to the stored cover letter file.")
    application_source: Optional[str] = Field(None, description="e.g., 'Website', 'Referral', 'LinkedIn'")
    current_status_id: Optional[int] = Field(None, description="Status ID from StatusSettings (e.g., Applied, Screening).")
    notes: Optional[str] = None
    linked_contact_id: Optional[str] = Field(None, description="Optional ID from Contacts table.") # Assuming Contact ID is str (UUID)

class CandidateCreate(CandidateBase):
    pass

class CandidateUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    application_source: Optional[str] = None
    current_status_id: Optional[int] = None
    notes: Optional[str] = None
    linked_contact_id: Optional[str] = None

class CandidateResponse(CandidateBase):
    candidate_id: str
    application_date: datetime
    # updated_at: Optional[datetime] # Schema for Candidates doesn't have updated_at

    class Config:
        orm_mode = True

# --- API Router for Candidates ---
router_candidates = APIRouter(tags=["Recruitment - Candidates"])

@router_candidates.post("/", response_model=CandidateResponse, status_code=201)
async def create_candidate_profile(candidate: CandidateCreate = Body(...)):
    """
    Create a new candidate profile.
    (File uploads for resume/cover letter would be handled in a more advanced setup,
     for now, paths are passed as strings).
    """
    # Ensure the referenced job_opening_id exists
    job_opening = recruitment_job_openings_crud.get_job_opening_by_id(candidate.job_opening_id)
    if not job_opening:
        raise HTTPException(status_code=404, detail=f"Job opening with ID {candidate.job_opening_id} not found.")

    candidate_data = candidate.dict(exclude_unset=True)
    new_candidate_id = recruitment_candidates_crud.add_candidate(candidate_data)
    if not new_candidate_id:
        raise HTTPException(status_code=500, detail="Failed to create candidate profile.")

    created_candidate = recruitment_candidates_crud.get_candidate_by_id(new_candidate_id)
    if not created_candidate:
         raise HTTPException(status_code=500, detail="Candidate created but failed to retrieve.")
    return created_candidate

@router_candidates.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate_profile(candidate_id: str):
    """
    Get a specific candidate by their ID.
    """
    candidate = recruitment_candidates_crud.get_candidate_by_id(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return candidate

@router_candidates.get("/", response_model=List[CandidateResponse])
async def list_all_candidates(
    job_opening_id: Optional[str] = Query(None, description="Filter by job opening ID."),
    email: Optional[EmailStr] = Query(None, description="Filter by candidate email."),
    current_status_id: Optional[int] = Query(None, description="Filter by current status ID."),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    List all candidates with optional filters.
    """
    filters = {}
    if job_opening_id:
        filters['job_opening_id'] = job_opening_id
    if email:
        filters['email'] = email
    if current_status_id is not None:
        filters['current_status_id'] = current_status_id

    candidates = recruitment_candidates_crud.get_all_candidates(filters=filters, limit=limit, offset=offset)
    return candidates

@router_job_openings.get("/{job_opening_id}/candidates", response_model=List[CandidateResponse], tags=["Recruitment - Job Openings"])
async def list_candidates_for_job_opening(
    job_opening_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    Get all candidates associated with a specific job opening.
    """
    # Verify job_opening_id exists
    job_opening = recruitment_job_openings_crud.get_job_opening_by_id(job_opening_id)
    if not job_opening:
        raise HTTPException(status_code=404, detail=f"Job opening with ID {job_opening_id} not found.")

    candidates = recruitment_candidates_crud.get_candidates_by_job_opening(job_opening_id=job_opening_id, limit=limit, offset=offset)
    return candidates

@router_candidates.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate_profile(candidate_id: str, candidate_update: CandidateUpdate = Body(...)):
    """
    Update an existing candidate's profile.
    """
    update_data = candidate_update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided.")

    # Check if candidate exists before attempting update
    existing_candidate = recruitment_candidates_crud.get_candidate_by_id(candidate_id)
    if not existing_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    # If job_opening_id is part of update_data, ensure it's valid (though not typical to change job via this)
    if 'job_opening_id' in update_data:
        job_opening = recruitment_job_openings_crud.get_job_opening_by_id(update_data['job_opening_id'])
        if not job_opening:
            raise HTTPException(status_code=404, detail=f"Referenced new job opening ID {update_data['job_opening_id']} not found.")

    success = recruitment_candidates_crud.update_candidate(candidate_id, update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update candidate profile.")

    updated_candidate = recruitment_candidates_crud.get_candidate_by_id(candidate_id)
    if not updated_candidate: # Should not happen
        raise HTTPException(status_code=500, detail="Candidate updated but failed to retrieve.")
    return updated_candidate

@router_candidates.delete("/{candidate_id}", status_code=204)
async def delete_candidate_profile(candidate_id: str):
    """
    Delete a specific candidate by their ID.
    """
    existing_candidate = recruitment_candidates_crud.get_candidate_by_id(candidate_id)
    if not existing_candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    success = recruitment_candidates_crud.delete_candidate(candidate_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete candidate profile.")
    return None

# Include Candidates router into the main recruitment router
router.include_router(router_candidates, prefix="/candidates")


# --- Pydantic Models for Interviews ---

class InterviewBase(BaseModel):
    candidate_id: str
    job_opening_id: str
    recruitment_step_id: Optional[str] = None
    interviewer_team_member_id: Optional[int] = None # Assuming TeamMember ID is int
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    interview_type: Optional[str] = Field(None, description="e.g., 'Phone', 'Video', 'On-site'")
    location_or_link: Optional[str] = None
    status_id: Optional[int] = Field(None, description="Status ID from StatusSettings (e.g., Scheduled, Completed).")
    feedback_notes_overall: Optional[str] = None
    feedback_rating: Optional[int] = Field(None, ge=1, le=5, description="Rating, e.g., 1-5 scale.")
    created_by_user_id: Optional[str] = None

class InterviewCreate(InterviewBase):
    pass

class InterviewUpdate(BaseModel):
    recruitment_step_id: Optional[str] = None
    interviewer_team_member_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    interview_type: Optional[str] = None
    location_or_link: Optional[str] = None
    status_id: Optional[int] = None
    feedback_notes_overall: Optional[str] = None
    feedback_rating: Optional[int] = Field(None, ge=1, le=5)

class InterviewResponse(InterviewBase):
    interview_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# --- API Router for Interviews ---
router_interviews = APIRouter(tags=["Recruitment - Interviews"])

@router_interviews.post("/", response_model=InterviewResponse, status_code=201)
async def schedule_interview(interview: InterviewCreate = Body(...)):
    """
    Schedule a new interview.
    """
    # Validate foreign keys
    if not recruitment_candidates_crud.get_candidate_by_id(interview.candidate_id):
        raise HTTPException(status_code=404, detail=f"Candidate with ID {interview.candidate_id} not found.")
    if not recruitment_job_openings_crud.get_job_opening_by_id(interview.job_opening_id):
        raise HTTPException(status_code=404, detail=f"Job Opening with ID {interview.job_opening_id} not found.")
    if interview.recruitment_step_id and not recruitment_steps_crud.get_recruitment_step_by_id(interview.recruitment_step_id):
        raise HTTPException(status_code=404, detail=f"Recruitment Step with ID {interview.recruitment_step_id} not found.")
    # Add validation for interviewer_team_member_id and created_by_user_id if TeamMembers/Users CRUDs are available and integrated

    interview_data = interview.dict(exclude_unset=True)
    new_interview_id = recruitment_interviews_crud.add_interview(interview_data)
    if not new_interview_id:
        raise HTTPException(status_code=500, detail="Failed to schedule interview.")

    created_interview = recruitment_interviews_crud.get_interview_by_id(new_interview_id)
    if not created_interview:
        raise HTTPException(status_code=500, detail="Interview scheduled but failed to retrieve.")
    return created_interview

@router_interviews.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview_details(interview_id: str):
    """
    Get details of a specific interview by its ID.
    """
    interview = recruitment_interviews_crud.get_interview_by_id(interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return interview

@router_interviews.get("/", response_model=List[InterviewResponse])
async def list_all_interviews(
    candidate_id: Optional[str] = Query(None),
    job_opening_id: Optional[str] = Query(None),
    interviewer_team_member_id: Optional[int] = Query(None), # Assuming int ID for team member
    status_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """
    List all interviews with optional filters.
    (Note: The CRUD function get_all_interviews needs to be implemented or adapted for filters)
    For now, this endpoint might be limited if the CRUD doesn't support these filters directly.
    Let's assume we will add a generic get_all_interviews to the CRUD or use specific ones.
    """
    # This is a placeholder; the actual CRUD `get_all_interviews` would need filter logic.
    # For now, we can use specific getters if filters are mutually exclusive or combine results.
    # This example will be simplified.
    interviews = []
    if candidate_id:
        interviews.extend(recruitment_interviews_crud.get_interviews_for_candidate(candidate_id, limit, offset))
    elif job_opening_id:
        interviews.extend(recruitment_interviews_crud.get_interviews_for_job_opening(job_opening_id, limit, offset))
    else:
        # A generic get_all_interviews(filters, limit, offset) would be ideal here.
        # If not available, this path might return an empty list or error.
        # Let's assume a basic get_all exists for now or this is a simplified example.
        # This is where you'd call `recruitment_interviews_crud.get_all_interviews(filters, limit, offset)`
        # For now, we'll return empty if no specific filter is used.
        # In a real app, you'd want a way to list all without specific candidate/job id if needed.
        pass # Resulting in empty list if no primary filter used.

    # This is a simplified placeholder for filtering. A real implementation
    # would pass all filters to a single CRUD function.
    filtered_interviews = interviews
    if interviewer_team_member_id is not None:
        filtered_interviews = [i for i in filtered_interviews if i.get('interviewer_team_member_id') == interviewer_team_member_id]
    if status_id is not None:
        filtered_interviews = [i for i in filtered_interviews if i.get('status_id') == status_id]

    # Apply limit and offset again if multiple calls were made and merged
    # This is not efficient for large datasets and should be handled by the DB query.
    return filtered_interviews[offset : offset + limit] if not (candidate_id or job_opening_id) else filtered_interviews


@router_interviews.put("/{interview_id}", response_model=InterviewResponse)
async def update_interview_details(interview_id: str, interview_update: InterviewUpdate = Body(...)):
    """
    Update an existing interview's details (e.g., feedback, status, time).
    """
    update_data = interview_update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided.")

    existing_interview = recruitment_interviews_crud.get_interview_by_id(interview_id)
    if not existing_interview:
        raise HTTPException(status_code=404, detail="Interview not found.")

    # Validate FKs if they are being updated
    if 'recruitment_step_id' in update_data and update_data['recruitment_step_id'] and \
       not recruitment_steps_crud.get_recruitment_step_by_id(update_data['recruitment_step_id']):
        raise HTTPException(status_code=404, detail=f"Recruitment Step with ID {update_data['recruitment_step_id']} not found.")

    success = recruitment_interviews_crud.update_interview(interview_id, update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update interview.")

    updated_interview = recruitment_interviews_crud.get_interview_by_id(interview_id)
    if not updated_interview: # Should not happen
        raise HTTPException(status_code=500, detail="Interview updated but failed to retrieve.")
    return updated_interview

@router_interviews.delete("/{interview_id}", status_code=204)
async def delete_scheduled_interview(interview_id: str):
    """
    Delete a specific interview by its ID.
    """
    existing_interview = recruitment_interviews_crud.get_interview_by_id(interview_id)
    if not existing_interview:
        raise HTTPException(status_code=404, detail="Interview not found.")

    success = recruitment_interviews_crud.delete_interview(interview_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete interview.")
    return None

# Include Interviews router into the main recruitment router
router.include_router(router_interviews, prefix="/interviews")


# --- Pydantic Models for Recruitment Steps ---

class RecruitmentStepBase(BaseModel):
    # job_opening_id is path param for add, or part of model for direct add
    step_name: str = Field(..., description="Name of the recruitment step (e.g., 'Phone Screen').")
    step_order: int = Field(..., description="Order of this step in the process.")
    description: Optional[str] = None

class RecruitmentStepCreate(RecruitmentStepBase):
    job_opening_id: str # Required when creating a new step directly

class RecruitmentStepUpdate(BaseModel):
    step_name: Optional[str] = None
    step_order: Optional[int] = None
    description: Optional[str] = None

class RecruitmentStepResponse(RecruitmentStepBase):
    recruitment_step_id: str
    job_opening_id: str # Include for context

    class Config:
        orm_mode = True

# --- API Router for Recruitment Steps (associated with Job Openings) ---
router_recruitment_steps = APIRouter(tags=["Recruitment - Recruitment Steps"])

@router_recruitment_steps.post("/job-openings/{job_opening_id}/steps", response_model=RecruitmentStepResponse, status_code=201)
async def add_step_to_job_opening(job_opening_id: str, step: RecruitmentStepBase = Body(...)):
    """
    Add a recruitment step to a specific job opening.
    """
    if not recruitment_job_openings_crud.get_job_opening_by_id(job_opening_id):
        raise HTTPException(status_code=404, detail=f"Job Opening with ID {job_opening_id} not found.")

    step_data = step.dict()
    step_data['job_opening_id'] = job_opening_id # Add job_opening_id from path

    new_step_id = recruitment_steps_crud.add_recruitment_step(step_data)
    if not new_step_id:
        raise HTTPException(status_code=500, detail="Failed to add recruitment step. Check for duplicate step_order or step_name for this job opening.")

    created_step = recruitment_steps_crud.get_recruitment_step_by_id(new_step_id)
    if not created_step:
        raise HTTPException(status_code=500, detail="Step created but failed to retrieve.")
    return created_step

@router_recruitment_steps.get("/job-openings/{job_opening_id}/steps", response_model=List[RecruitmentStepResponse])
async def list_steps_for_job_opening(job_opening_id: str):
    """
    List all recruitment steps for a specific job opening, ordered by step_order.
    """
    if not recruitment_job_openings_crud.get_job_opening_by_id(job_opening_id):
        raise HTTPException(status_code=404, detail=f"Job Opening with ID {job_opening_id} not found.")

    steps = recruitment_steps_crud.get_recruitment_steps_for_job_opening(job_opening_id)
    return steps

@router_recruitment_steps.get("/steps/{recruitment_step_id}", response_model=RecruitmentStepResponse)
async def get_single_recruitment_step(recruitment_step_id: str):
    """
    Get a specific recruitment step by its ID.
    """
    step = recruitment_steps_crud.get_recruitment_step_by_id(recruitment_step_id)
    if not step:
        raise HTTPException(status_code=404, detail="Recruitment step not found.")
    return step

@router_recruitment_steps.put("/steps/{recruitment_step_id}", response_model=RecruitmentStepResponse)
async def update_single_recruitment_step(recruitment_step_id: str, step_update: RecruitmentStepUpdate = Body(...)):
    """
    Update a specific recruitment step.
    """
    update_data = step_update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided.")

    existing_step = recruitment_steps_crud.get_recruitment_step_by_id(recruitment_step_id)
    if not existing_step:
        raise HTTPException(status_code=404, detail="Recruitment step not found.")

    success = recruitment_steps_crud.update_recruitment_step(recruitment_step_id, update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update recruitment step. Possible duplicate step_order or step_name for the job opening.")

    updated_step = recruitment_steps_crud.get_recruitment_step_by_id(recruitment_step_id)
    if not updated_step:
        raise HTTPException(status_code=500, detail="Step updated but failed to retrieve.")
    return updated_step

@router_recruitment_steps.delete("/steps/{recruitment_step_id}", status_code=204)
async def delete_single_recruitment_step(recruitment_step_id: str):
    """
    Delete a specific recruitment step.
    """
    existing_step = recruitment_steps_crud.get_recruitment_step_by_id(recruitment_step_id)
    if not existing_step:
        raise HTTPException(status_code=404, detail="Recruitment step not found.")

    success = recruitment_steps_crud.delete_recruitment_step(recruitment_step_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete recruitment step.")
    return None

# Include Recruitment Steps router into the main recruitment router
# This makes routes like /recruitment/job-openings/{job_opening_id}/steps available
router.include_router(router_recruitment_steps)


# --- Pydantic Models for Candidate Progress ---

class CandidateProgressBase(BaseModel):
    # candidate_id and recruitment_step_id are often path params or part of a composite key logic
    status_id: Optional[int] = Field(None, description="Status ID from StatusSettings (e.g., Pending, Completed).")
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None

class CandidateProgressCreate(CandidateProgressBase):
    candidate_id: str
    recruitment_step_id: str

class CandidateProgressUpdate(CandidateProgressBase): # Can update status, notes, completed_at
    pass


class CandidateProgressResponse(CandidateProgressBase):
    candidate_progress_id: str
    candidate_id: str
    recruitment_step_id: str
    updated_at: datetime
    # Optionally include step details if joining in CRUD
    step_name: Optional[str] = None
    step_order: Optional[int] = None


    class Config:
        orm_mode = True

# --- API Router for Candidate Progress ---
router_candidate_progress = APIRouter(tags=["Recruitment - Candidate Progress"])

@router_candidate_progress.post("/progress", response_model=CandidateProgressResponse, status_code=201)
async def add_or_update_candidate_progress_entry(progress: CandidateProgressCreate = Body(...)):
    """
    Add or update a candidate's progress at a specific recruitment step.
    If a record for this candidate_id and recruitment_step_id exists, it can be updated.
    If not, a new one is created.
    The CRUD function `add_candidate_progress` handles insert. Update is separate.
    This endpoint will primarily focus on adding. For updates, use PUT.
    """
    # Validate FKs
    if not recruitment_candidates_crud.get_candidate_by_id(progress.candidate_id):
        raise HTTPException(status_code=404, detail=f"Candidate {progress.candidate_id} not found.")
    if not recruitment_steps_crud.get_recruitment_step_by_id(progress.recruitment_step_id):
        raise HTTPException(status_code=404, detail=f"Recruitment Step {progress.recruitment_step_id} not found.")

    # Check if progress for this candidate at this step already exists
    existing_progress = recruitment_candidate_progress_crud.get_progress_for_candidate_at_step(
        progress.candidate_id, progress.recruitment_step_id
    )
    if existing_progress:
        raise HTTPException(status_code=409,
                            detail=f"Progress for candidate {progress.candidate_id} at step {progress.recruitment_step_id} already exists. Use PUT to update.",
                            headers={"X-Existing-Progress-ID": existing_progress['candidate_progress_id']})

    progress_data = progress.dict()
    new_progress_id = recruitment_candidate_progress_crud.add_candidate_progress(progress_data)
    if not new_progress_id:
        raise HTTPException(status_code=500, detail="Failed to add candidate progress.")

    created_progress = recruitment_candidate_progress_crud.get_candidate_progress_by_id(new_progress_id)
    if not created_progress:
        raise HTTPException(status_code=500, detail="Progress added but failed to retrieve.")
    return created_progress

@router_candidate_progress.get("/candidates/{candidate_id}/progress", response_model=List[CandidateProgressResponse])
async def get_all_progress_for_candidate(candidate_id: str):
    """
    Get all progress entries for a specific candidate, typically ordered by step_order.
    """
    if not recruitment_candidates_crud.get_candidate_by_id(candidate_id):
        raise HTTPException(status_code=404, detail=f"Candidate with ID {candidate_id} not found.")

    progress_list = recruitment_candidate_progress_crud.get_progress_for_candidate(candidate_id)
    return progress_list

@router_candidate_progress.get("/candidates/{candidate_id}/progress/{recruitment_step_id}", response_model=CandidateProgressResponse)
async def get_specific_candidate_progress(candidate_id: str, recruitment_step_id: str):
    """
    Get a candidate's progress for a specific recruitment step.
    """
    if not recruitment_candidates_crud.get_candidate_by_id(candidate_id):
        raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found.")
    if not recruitment_steps_crud.get_recruitment_step_by_id(recruitment_step_id):
        raise HTTPException(status_code=404, detail=f"Recruitment Step {recruitment_step_id} not found.")

    progress = recruitment_candidate_progress_crud.get_progress_for_candidate_at_step(candidate_id, recruitment_step_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Candidate progress not found for this step.")
    return progress

@router_candidate_progress.put("/progress/{candidate_progress_id}", response_model=CandidateProgressResponse)
async def update_specific_candidate_progress_entry(candidate_progress_id: str, progress_update: CandidateProgressUpdate = Body(...)):
    """
    Update a specific candidate progress entry by its unique ID.
    """
    update_data = progress_update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided.")

    existing_progress = recruitment_candidate_progress_crud.get_candidate_progress_by_id(candidate_progress_id)
    if not existing_progress:
        raise HTTPException(status_code=404, detail="Candidate progress record not found.")

    success = recruitment_candidate_progress_crud.update_candidate_progress(candidate_progress_id, update_data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update candidate progress.")

    updated_progress = recruitment_candidate_progress_crud.get_candidate_progress_by_id(candidate_progress_id)
    if not updated_progress: # Should not happen
        raise HTTPException(status_code=500, detail="Progress updated but failed to retrieve.")
    return updated_progress

@router_candidate_progress.delete("/progress/{candidate_progress_id}", status_code=204)
async def delete_specific_candidate_progress_entry(candidate_progress_id: str):
    """
    Delete a specific candidate progress entry by its ID.
    """
    existing_progress = recruitment_candidate_progress_crud.get_candidate_progress_by_id(candidate_progress_id)
    if not existing_progress:
        raise HTTPException(status_code=404, detail="Candidate progress record not found.")

    success = recruitment_candidate_progress_crud.delete_candidate_progress(candidate_progress_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete candidate progress record.")
    return None

# Include Candidate Progress router into the main recruitment router
router.include_router(router_candidate_progress)

# The main `router` from this file should be included in api/main.py
# Example in api/main.py:
# from . import recruitment
# app.include_router(recruitment.router)
```

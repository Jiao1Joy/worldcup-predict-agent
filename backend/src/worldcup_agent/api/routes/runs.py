import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from worldcup_agent.api.schemas import ApprovalRequest, CreateRunRequest, FailureRequest
from worldcup_agent.domain.models import RunEvent
from worldcup_agent.runtime.replay import replay_run
from worldcup_agent.runtime.service import AgentRuntimeService

router = APIRouter(prefix="/api/runs", tags=["runs"])


def format_sse(event: RunEvent) -> str:
    return (
        f"id: {event.sequence}\n"
        f"event: {event.event_type.value}\n"
        f"data: {event.model_dump_json()}\n\n"
    )


def get_service(request: Request) -> AgentRuntimeService:
    return request.app.state.runtime_service


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_run(payload: CreateRunRequest, service: AgentRuntimeService = Depends(get_service)):
    state = await service.create_run(
        {
            "intent": "predict_tournament",
            "task": payload.task,
            "seed": payload.seed,
            "data_conflict": payload.data_conflict,
        }
    )
    return state.model_dump(mode="json")


@router.get("/{run_id}")
async def get_run(run_id: str, service: AgentRuntimeService = Depends(get_service)):
    try:
        state = await replay_run(service.store, run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    return state.model_dump(mode="json")


@router.get("/{run_id}/initial")
async def get_initial_run(run_id: str, service: AgentRuntimeService = Depends(get_service)):
    try:
        state = await service.store.get_initial_state(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    return state.model_dump(mode="json")


@router.post("/{run_id}/start")
async def start_run(run_id: str, service: AgentRuntimeService = Depends(get_service)):
    state = await service.run(run_id)
    return state.model_dump(mode="json")


@router.post("/{run_id}/inject-failure")
async def inject_failure(
    run_id: str,
    payload: FailureRequest,
    service: AgentRuntimeService = Depends(get_service),
):
    state = await service.run(run_id, inject_failure=payload.failure)
    return state.model_dump(mode="json")


@router.post("/{run_id}/approve")
async def approve(
    run_id: str,
    payload: ApprovalRequest,
    service: AgentRuntimeService = Depends(get_service),
):
    state = await service.approve(run_id, payload.choice, payload.actor)
    return state.model_dump(mode="json")


@router.get("/{run_id}/events")
async def stream_events(run_id: str, request: Request, service: AgentRuntimeService = Depends(get_service)):
    async def event_source():
        after = int(request.headers.get("last-event-id", "0"))
        while not await request.is_disconnected():
            events = await service.store.list_events(run_id, after=after)
            for event in events:
                after = event.sequence
                yield format_sse(event)
            await asyncio.sleep(0.25)

    return StreamingResponse(event_source(), media_type="text/event-stream")

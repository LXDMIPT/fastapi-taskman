import asyncio
import time
from sqlalchemy.sql import text
import httpx
from fastapi import APIRouter, status, Depends, HTTPException, Response
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_async_session
from ..schemas import task as schema_task
from typing import List
from datetime import date

router = APIRouter(prefix="/v2/async", tags=["Асинхронные операции"])


@router.get("/tasks", status_code=status.HTTP_200_OK,
            response_model=List[schema_task.TaskRead])
async def read_tasks_async(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(schema_task.Task))
    tasks = result.scalars().all()
    if tasks is None or len(tasks) == 0:
        raise HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail=f"The task list is empty."
        )
    return tasks


@router.get("/tasks-for-day", status_code=status.HTTP_200_OK)
async def read_tasks_for_day(response: Response,
                             session: AsyncSession = Depends(get_async_session),
                             due_date: date = date.today()):
    start = time.time()
    async def query_db(due_date_param):
        statement = (select(schema_task.Task)
                     .where(schema_task.Task.due_date == due_date_param))
        result = await session.execute(statement)
        return result.scalars().all()


    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=None))
    res = await asyncio.gather(
        query_db(due_date),
        http_client.get(f"https://isdayoff.ru/{due_date}"),
        #session.execute(text("SELECT pg_sleep(5)")),
        #http_client.get("https://httpbin.org/delay/10"),
    )

    elapsed_seconds = time.time() - start
    output = [{
        "due_date": due_date,
        "is_day_off": True if res[1].text == "1" else False,
        "tasks": res[0]
    }]

    response.headers["X-Completed-In"] = f"{elapsed_seconds:.3f} seconds"
    return output

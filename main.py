import asyncio
import os
from contextlib import asynccontextmanager
from functools import reduce
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from starlette.responses import FileResponse
from tortoise import Tortoise, connections

from database.config import TORTOISE_ORM
from db_connector import get_running_instances_log
from bpmn_model import BpmnModel, get_model_for_instance, UserFormMessage

models = {}
for file in os.listdir("models"):
    if file.endswith(".bpmn"):
        m = BpmnModel(file)
        models[file] = m


@asynccontextmanager
async def lifespan(app: FastAPI):
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()
    print(models)
    app.state.bpmn_models = models
    log = await get_running_instances_log()
    for l in log:
        for key, data in l.items():
            if data["model_path"] in app.state.bpmn_models:
                instance = await app.state.bpmn_models[data["model_path"]].create_instance(
                    key, {}
                )
                instance = await instance.run_from_log(data["events"])
    yield
    await connections.close_all()

app = FastAPI(lifespan=lifespan)


@app.get("/model")
async def get_models():
    data = [m.to_json() for m in models.values()]
    return {"status": "ok", "results": data}


@app.get("/model/{model_name}")
async def get_model(request: Request, model_name):
    return FileResponse(path=os.path.join("models", request.app.state.bpmn_models[model_name].model_path))


@app.post("/model/{model_name}/instance")
async def handle_new_instance(request: Request, model_name):
    _id = str(uuid4())
    instance = await request.app.state.bpmn_models[model_name].create_instance(_id, {})
    asyncio.create_task(instance.run())
    return {"id": _id}


@app.post("/instance/{instance_id}/task/{task_id}/form")
async def handle_form(instance_id, task_id, post: dict):
    m = get_model_for_instance(instance_id)
    m.instances[instance_id].in_queue.put_nowait(UserFormMessage(task_id, post))

    return {"status": "OK"}


@app.get("/instance")
async def search_instance(request: Request):
    params = request.query_params
    queries = []
    try:
        strip_lower = lambda x: x.strip().lower()
        check_colon = lambda x: x if ":" in x else f":{x}"

        queries = list(
            tuple(
                map(
                    strip_lower,
                    check_colon(q).split(":"),
                )
            )
            for q in params["q"].split(",")
        )
    except:
        return {"error": "invalid_query"}

    result_ids = []
    for (att, value) in queries:
        ids = []
        for m in models.values():
            for _id, instance in m.instances.items():
                search_atts = []
                if not att:
                    search_atts = list(instance.variables.keys())
                else:
                    for key in instance.variables.keys():
                        if not att or att in key.lower():
                            search_atts.append(key)
                search_atts = filter(
                    lambda x: isinstance(instance.variables[x], str), search_atts
                )

                for search_att in search_atts:
                    if search_att and value in instance.variables[search_att].lower():
                        # data.append(instance.to_json())
                        ids.append(_id)
        result_ids.append(set(ids))

    ids = reduce(lambda a, x: a.intersection(x), result_ids[:-1], result_ids[0])

    data = []
    for _id in ids:
        data.append(get_model_for_instance(_id).instances[_id].to_json())

    return {"status": "ok", "results": data}


@app.get("/instance/{instance_id}/task/{task_id}")
async def handle_task_info(instance_id, task_id):
    m = get_model_for_instance(instance_id)
    if not m:
        raise HTTPException(400, "not found")
    instance = m.instances[instance_id]
    task = instance.model.elements[task_id]

    return task.get_info()


@app.get("/instance/{instance_id}")
async def handle_instance_info(instance_id):
    m = get_model_for_instance(instance_id)
    if not m:
        raise HTTPException(400, "not found")
    instance = m.instances[instance_id].to_json()
    return instance


if __name__ == '__main__':
    uvicorn.run("main:app")

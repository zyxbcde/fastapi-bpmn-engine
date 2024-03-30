from datetime import datetime
from typing import List

from database.models import Event, RunningInstance


async def add_event(model_name: str,
                    instance_id: int,
                    activity_id: int,
                    timestamp: datetime,
                    pending: List[str],
                    activity_variables: dict
                    ):
    await Event.create(model_name=model_name,
                       instance_id=instance_id,
                       activity_id=activity_id,
                       timestamp=timestamp,
                       pending=pending,
                       activity_variables=activity_variables,
                       )


async def add_running_instance(instance_id: int):
    await RunningInstance.create(instance_id=instance_id, running=True)


async def finish_running_instance(instance: int):
    await RunningInstance.filter(instance_id=instance).update(running=False)


async def get_running_instances_log():
    log = []
    running_instances = await RunningInstance.filter(running=True).all()
    for instance in running_instances:
        instance_dict = {}
        instance_dict[instance.instance_id] = {}
        events = await Event.filter(instance_id = instance.instance_id).all().order_by("timestamp")
        events_list = []
        for event in events:
            model_path = event.model_name
            event_dict = {}
            event_dict["activity_id"] = event.activity_id
            event_dict["pending"] = event.pending
            event_dict["activity_variables"] = event.activity_variables
            events_list.append(event_dict)

        instance_dict[instance.instance_id]["model_path"] = model_path
        instance_dict[instance.instance_id]["events"] = events_list
        log.append(instance_dict)

    return log

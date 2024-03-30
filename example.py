import asyncio
import random

from tortoise import run_async, Tortoise

from bpmn_model import BpmnModel, UserFormMessage
from database.config import TORTOISE_ORM

m = BpmnModel("model_01.bpmn")
NUM_INSTANCES = 2


async def get_workload():
    return [await m.create_instance(str(i + 1), {}) for i in range(NUM_INSTANCES)]


async def simulate_user(q):
    WAIT = 0.01

    def auto(text):
        return ""

    def ask(text):
        text = auto(text)
        # sys.stdout.write(f"\t[?] {text}")
        # sys.stdout.flush()
        # text = sys.stdin.readline().strip()
        return (
            {
                key: value
                for statement in (text.split(",") if "," in text else [text])
                for key, value in statement.split("=")
            }
            if text
            else {}
        )

    q.put_nowait(UserFormMessage("start_process", "null"))  # Wrong message
    await asyncio.sleep(WAIT)

    a = random.randint(1, 2)
    default = f"option={a}"
    data = ask(f"Form input: [{default}]")
    q.put_nowait(UserFormMessage("t0", data if data != "" else default))
    await asyncio.sleep(WAIT)

    q.put_nowait(UserFormMessage("tup", ask("Form input [tup]: ")))
    await asyncio.sleep(WAIT)

    q.put_nowait(UserFormMessage("t_wrong", "null"))  # Wrong message
    await asyncio.sleep(WAIT)

    q.put_nowait(UserFormMessage("tdown", ask("Form input [tdown]: ")))
    await asyncio.sleep(WAIT)

    q.put_nowait(UserFormMessage("t_wrong", "null"))  # Wrong message
    await asyncio.sleep(WAIT)

    q.put_nowait(UserFormMessage("tup2", ask("Form input [tup2]: ")))
    await asyncio.sleep(WAIT)

    q.put_nowait(UserFormMessage("t_wrong", "null"))  # Wrong message
    await asyncio.sleep(WAIT)

    q.put_nowait(UserFormMessage("tdown2", ask("Form input [tdown2]: ")))
    await asyncio.sleep(WAIT)


async def serial():
    await Tortoise.init(config=TORTOISE_ORM)
    instances = await get_workload()
    for i, p in enumerate(instances):
        print(f"Running process {i + 1}\n-----------------")
        await asyncio.gather(simulate_user(p.in_queue), p.run())


async def parallel():
    instances = await get_workload()
    users = [simulate_user(i.in_queue) for i in instances]
    processes = [p.run() for p in instances]
    await asyncio.gather(*users, *processes)

    print(f"Running processes\n-----------------")


if __name__ == '__main__':
    run_async(serial())
    print("END")

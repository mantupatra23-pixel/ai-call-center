from rq import Worker, Queue, Connection
import redis

redis_conn = redis.Redis(host="localhost", port=6379)
with Connection(redis_conn):
    worker = Worker([Queue("calls")])
    worker.work()

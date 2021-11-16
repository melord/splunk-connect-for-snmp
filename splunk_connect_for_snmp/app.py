from celery import Celery, signals
from celery.utils.log import get_task_logger
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from splunk_connect_for_snmp import customtaskmanager

provider = TracerProvider()
processor = BatchSpanProcessor(JaegerExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

logger = get_task_logger(__name__)


app = Celery("sc4snmp")
app.config_from_object("splunk_connect_for_snmp.celery_config")

app.autodiscover_tasks(
    packages=[
        "splunk_connect_for_snmp",
        "splunk_connect_for_snmp.enrich",
        "splunk_connect_for_snmp.inventory",
        "splunk_connect_for_snmp.snmp",
        "splunk_connect_for_snmp.splunk",
    ]
)


@signals.worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    CeleryInstrumentor().instrument()
    LoggingInstrumentor().instrument()


@signals.beat_init.connect(weak=False)
def init_celery_beat_tracing(*args, **kwargs):
    CeleryInstrumentor().instrument()
    LoggingInstrumentor().instrument()


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs) -> None:

    schedule_data_create_interval = {
        "name": "sc4snmp;inventory;seed",
        "task": "splunk_connect_for_snmp.inventory.tasks.inventory_seed",
        "args": [],
        "kwargs": {
            "url": "https://gist.githubusercontent.com/rfaircloth-splunk/0590fa671f794902005257bcbd2ee274/raw/90f6930aaace6ca5aba8edc8c57f38552049c1d1/snmp_inventory.csv"
        },
        "interval": {"every": 20, "period": "seconds"},
        "enabled": True,
        "run_immediately": True,
    }

    periodic_obj = customtaskmanager.CustomPeriodicTaskManage()
    periodic_obj.manage_task(**schedule_data_create_interval)

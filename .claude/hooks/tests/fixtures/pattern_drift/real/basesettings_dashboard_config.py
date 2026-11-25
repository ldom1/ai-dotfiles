import logging
import os
from typing import Any

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

_log = logging.getLogger(__name__)
_PREFIX = "DASHBOARD_"


class HomelabApp(BaseModel):
    name: str
    url: str


class BusinessProduct(BaseModel):
    id: str
    name: str
    url: str
    umami_site_id: str
    gsc_property: str


class InfisicalSettingsSource(PydanticBaseSettingsSource):
    """Secrets from Infisical (Universal Auth); no-op without INFISICAL_CLIENT_ID."""

    _PATHS: tuple[str, ...] = ("/",)

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        return None, field_name, False  # unused: __call__ is overridden

    def __call__(self) -> dict[str, Any]:
        client_id = os.environ.get("INFISICAL_CLIENT_ID")
        if not client_id:
            return {}
        client_secret = os.environ.get("INFISICAL_CLIENT_SECRET")
        project_id = os.environ.get("INFISICAL_PROJECT_ID")
        missing = [
            name
            for name, value in (
                ("INFISICAL_CLIENT_SECRET", client_secret),
                ("INFISICAL_PROJECT_ID", project_id),
            )
            if not value
        ]
        if missing:
            raise ValueError(
                f"INFISICAL_CLIENT_ID is set but {', '.join(missing)} missing"
            )
        from infisical_sdk import InfisicalSDKClient  # lazy: optional at runtime

        secrets: dict[str, Any] = {}
        try:
            client = InfisicalSDKClient(
                host=os.environ.get("INFISICAL_HOST", "https://infisical.dombot.tech")
            )
            client.auth.universal_auth.login(
                client_id=client_id, client_secret=client_secret
            )
            for path in self._PATHS:
                listing = client.secrets.list_secrets(
                    project_id=project_id,
                    environment_slug=os.environ.get("INFISICAL_ENV", "prod"),
                    secret_path=path,
                    view_secret_value=True,
                )
                for item in listing.secrets:
                    if not item.secretKey.startswith(_PREFIX):
                        _log.warning(
                            "Infisical: ignoring key without %s prefix", _PREFIX
                        )
                        continue
                    name = item.secretKey[len(_PREFIX) :].lower()
                    if name.split("__")[0] not in self.settings_cls.model_fields:
                        _log.warning(
                            "Infisical: ignoring unknown setting %s", item.secretKey
                        )
                        continue
                    secrets[name] = item.secretValue
        except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            _log.warning("Infisical unreachable, business sources will error: %s", exc)
            return {}
        return secrets


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DASHBOARD_",
        env_nested_delimiter="__",
    )

    @classmethod
    def settings_customise_sources(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # env vars win over Infisical so Coolify-level overrides keep working
        return (
            init_settings,
            env_settings,
            InfisicalSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    prometheus_url: str = "http://host.docker.internal:9090"
    poll_interval_seconds: int = 15
    # node_exporter's textfile collector labels node_textfile_mtime_seconds with
    # the file's full path, not its basename — must match server-setup's
    # homelab_metrics_textfile role output path exactly (the fixed interface
    # contract both repos document), or the staleness query in metrics.py silently
    # never matches and every textfile-sourced widget reads as permanently stale.
    textfile_name: str = "/var/lib/node_exporter/textfile_collector/homelab_custom.prom"
    tailscale_expected_peers: int = 3
    host_name: str = "hp-elite-server"
    grafana_dashboard_url: str = (
        "https://grafana.dombot.tech/d/hp-elite-server-overview"
    )
    coolify: HomelabApp = HomelabApp(name="Coolify", url="https://coolify.dombot.tech")
    immich: HomelabApp = HomelabApp(name="Immich", url="https://immich.dombot.tech")
    grafana: HomelabApp = HomelabApp(name="Grafana", url="https://grafana.dombot.tech")
    infisical: HomelabApp = HomelabApp(
        name="Infisical", url="https://infisical.dombot.tech"
    )
    paperless_ngx: HomelabApp = HomelabApp(
        name="Paperless-ngx", url="https://paperless-ngx.dombot.tech"
    )
    stirling_pdf: HomelabApp = HomelabApp(
        name="Stirling PDF", url="https://stirling-pdf.dombot.tech"
    )
    paperless_stirling_bridge: HomelabApp = HomelabApp(
        name="Paperless-Stirling Bridge",
        url="https://paperless-stirling-bridge.dombot.tech",
    )
    privatebin: HomelabApp = HomelabApp(
        name="PrivateBin", url="https://private-bin.dombot.tech"
    )
    calendar: HomelabApp = HomelabApp(
        name="Calendrier", url="https://calendrier.dombot.tech/agenda/"
    )
    cloudreve: HomelabApp = HomelabApp(
        name="Cloudreve", url="https://cloudreve.dombot.tech"
    )
    voicestudio: HomelabApp = HomelabApp(
        name="VoiceStudio", url="https://voicestudio.dombot.tech"
    )
    umami: HomelabApp = HomelabApp(
        name="Umami", url="https://umami-web-analytics.dombot.tech"
    )
    notion_pilot: HomelabApp = HomelabApp(
        name="Notion Pilot", url="https://notion-pilot.dombot.tech"
    )
    domosint: HomelabApp = HomelabApp(
        name="Domosint", url="https://domosint.dombot.tech"
    )
    messidor: HomelabApp = HomelabApp(
        name="Messidor", url="https://messidor.dombot.tech"
    )
    marketing_ops: HomelabApp = HomelabApp(
        name="Marketing Ops", url="https://marketing-ops.dombot.tech"
    )
    briefing: HomelabApp = HomelabApp(
        name="Briefing", url="https://briefing.dombot.tech"
    )
    business_products: tuple[BusinessProduct, ...] = (
        BusinessProduct(
            id="notion-pilot",
            name="Notion Pilot",
            url="https://notion-pilot.com",
            umami_site_id="c38fe16b-eadb-4f2b-9966-d9399ffe4a40",
            gsc_property="sc-domain:notion-pilot.com",
        ),
        BusinessProduct(
            id="prosper",
            name="Prosper",
            url="https://prospers.fr",
            umami_site_id="eab3bd4f-b412-464d-bfa5-2818d985d503",
            gsc_property="sc-domain:prospers.fr",
        ),
        BusinessProduct(
            id="epidemie-des-mots",
            name="Épidémie des mots",
            url="https://www.epidemiedesmots.fr",
            umami_site_id="1e24506c-82f4-49c0-b6e7-dc62f45d42cc",
            gsc_property="sc-domain:epidemiedesmots.fr",
        ),
    )
    umami_url: str = "https://umami-web-analytics.dombot.tech"
    umami_host_header: str = ""
    umami_user: str = ""
    umami_password: str = ""
    gsc_service_account_json: str = ""
    stripe_key: str = ""
    np_mongo_dsn: str = ""
    np_mongo_db: str = ""
    epi_mongo_dsn: str = ""
    epi_mongo_db: str = ""
    prosper_pg_dsn: str = ""
    payhip_secret: str = ""
    business_db_path: str = "/data/business.sqlite"
    business_refresh_seconds: int = 3600
    business_stale_after_seconds: int = 21600
    metrics_json_path: str = ""
    techspend_catalog_path: str = "techspend.yaml"
    techspend_db_path: str = "/data/techspend.sqlite"
    techspend_tick_seconds: int = 3600  # 0 disables the refresher thread
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    openrouter_api_key: str = ""
    openrouter_management_key: str = ""  # /api/v1/credits only
    atlas_size_dsn: str = ""
    supabase_mesure_prod_dsn: str = ""
    supabase_mesure_preprod_dsn: str = ""

    def homelab_apps(self) -> tuple[HomelabApp, ...]:
        return (
            self.coolify,
            self.immich,
            self.grafana,
            self.infisical,
            self.paperless_ngx,
            self.stirling_pdf,
            self.paperless_stirling_bridge,
            self.privatebin,
            self.cloudreve,
            self.voicestudio,
            self.calendar,
            self.umami,
            self.notion_pilot,
            self.domosint,
            self.messidor,
            self.marketing_ops,
            self.briefing,
        )


settings = Settings()

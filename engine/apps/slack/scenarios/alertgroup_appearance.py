import json
import typing

from apps.api.permissions import RBACPermission
from apps.slack.chatops_proxy_routing import make_private_metadata
from apps.slack.scenarios import scenario_step
from apps.slack.types import (
    Block,
    BlockActionType,
    EventPayload,
    InteractiveMessageActionType,
    ModalView,
    PayloadType,
    ScenarioRoute,
)

from .step_mixins import AlertGroupActionsMixin

if typing.TYPE_CHECKING:
    from apps.slack.models import SlackTeamIdentity, SlackUserIdentity
    from apps.user_management.models import Organization


class OpenAlertAppearanceDialogStep(AlertGroupActionsMixin, scenario_step.ScenarioStep):
    REQUIRED_PERMISSIONS = [RBACPermission.Permissions.CHATOPS_WRITE]

    def process_scenario(
        self,
        slack_user_identity: "SlackUserIdentity",
        slack_team_identity: "SlackTeamIdentity",
        payload: "EventPayload",
        predefined_org: typing.Optional["Organization"] = None,
    ) -> None:
        alert_group = self.get_alert_group(slack_team_identity, payload)
        if not self.is_authorized(alert_group):
            self.open_unauthorized_warning(payload)
            return

        private_metadata = {
            "organization_id": self.organization.pk,
            "alert_group_pk": alert_group.pk,
            "message_ts": payload.get("message_ts") or payload["container"]["message_ts"],
        }

        alert_receive_channel = alert_group.channel
        blocks: typing.List[Block.Section] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":point_right: Click <{alert_receive_channel.web_link}|here> to open Integrations settings, edit Slack templates and return here",
                },
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": "Once changed Refresh the alert group"}},
        ]

        view: ModalView = {
            "callback_id": UpdateAppearanceStep.routing_uid(),
            "blocks": blocks,
            "type": "modal",
            "title": {
                "type": "plain_text",
                "text": "Alert group template",
            },
            "submit": {
                "type": "plain_text",
                "text": "Refresh alert group",
            },
            "private_metadata": make_private_metadata(private_metadata, alert_receive_channel.organization),
        }

        self._slack_client.views_open(trigger_id=payload["trigger_id"], view=view)


class UpdateAppearanceStep(scenario_step.ScenarioStep):
    def process_scenario(
        self,
        slack_user_identity: "SlackUserIdentity",
        slack_team_identity: "SlackTeamIdentity",
        payload: "EventPayload",
        predefined_org: typing.Optional["Organization"] = None,
    ) -> None:
        from apps.alerts.models import AlertGroup

        private_metadata = json.loads(payload["view"]["private_metadata"])
        alert_group = AlertGroup.objects.get(pk=private_metadata["alert_group_pk"])
        slack_message = alert_group.slack_message

        self._slack_client.chat_update(
            # TODO: once _channel_id has been fully migrated to channel, remove _channel_id
            # see https://raintank-corp.slack.com/archives/C06K1MQ07GS/p173255546
            # channel=slack_message.channel.slack_id,
            channel=slack_message._channel_id,
            ts=slack_message.slack_id,
            attachments=alert_group.render_slack_attachments(),
            blocks=alert_group.render_slack_blocks(),
        )


STEPS_ROUTING: ScenarioRoute.RoutingSteps = [
    {
        "payload_type": PayloadType.INTERACTIVE_MESSAGE,
        "action_type": InteractiveMessageActionType.BUTTON,
        "action_name": OpenAlertAppearanceDialogStep.routing_uid(),
        "step": OpenAlertAppearanceDialogStep,
    },
    {
        "payload_type": PayloadType.BLOCK_ACTIONS,
        "block_action_type": BlockActionType.BUTTON,
        "block_action_id": OpenAlertAppearanceDialogStep.routing_uid(),
        "step": OpenAlertAppearanceDialogStep,
    },
    {
        "payload_type": PayloadType.VIEW_SUBMISSION,
        "view_callback_id": UpdateAppearanceStep.routing_uid(),
        "step": UpdateAppearanceStep,
    },
]

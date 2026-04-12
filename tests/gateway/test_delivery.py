"""Tests for the delivery routing module."""

from gateway.config import GatewayConfig, HomeChannel, Platform, PlatformConfig
from gateway.delivery import DeliveryRouter, DeliveryTarget
from gateway.session import SessionSource


class TestParseTargetPlatformChat:
    def test_explicit_telegram_chat(self):
        target = DeliveryTarget.parse("telegram:12345")
        assert target.platform == Platform.TELEGRAM
        assert target.chat_id == "12345"
        assert target.is_explicit is True

    def test_platform_only_no_chat_id(self):
        target = DeliveryTarget.parse("discord")
        assert target.platform == Platform.DISCORD
        assert target.chat_id is None
        assert target.is_explicit is False

    def test_local_target(self):
        target = DeliveryTarget.parse("local")
        assert target.platform == Platform.LOCAL
        assert target.chat_id is None

    def test_origin_with_source(self):
        origin = SessionSource(platform=Platform.TELEGRAM, chat_id="789", thread_id="42")
        target = DeliveryTarget.parse("origin", origin=origin)
        assert target.platform == Platform.TELEGRAM
        assert target.chat_id == "789"
        assert target.thread_id == "42"
        assert target.is_origin is True

    def test_origin_without_source(self):
        target = DeliveryTarget.parse("origin")
        assert target.platform == Platform.LOCAL
        assert target.is_origin is True

    def test_unknown_platform(self):
        target = DeliveryTarget.parse("unknown_platform")
        assert target.platform == Platform.LOCAL


class TestTargetToStringRoundtrip:
    def test_origin_roundtrip(self):
        origin = SessionSource(platform=Platform.TELEGRAM, chat_id="111", thread_id="42")
        target = DeliveryTarget.parse("origin", origin=origin)
        assert target.to_string() == "origin"

    def test_local_roundtrip(self):
        target = DeliveryTarget.parse("local")
        assert target.to_string() == "local"

    def test_platform_only_roundtrip(self):
        target = DeliveryTarget.parse("discord")
        assert target.to_string() == "discord"

    def test_explicit_chat_roundtrip(self):
        target = DeliveryTarget.parse("telegram:999")
        s = target.to_string()
        assert s == "telegram:999"

        reparsed = DeliveryTarget.parse(s)
        assert reparsed.platform == Platform.TELEGRAM
        assert reparsed.chat_id == "999"


class TestResolveTargets:
    def test_platform_only_uses_home_channel(self):
        config = GatewayConfig(
            platforms={
                Platform.SLACK: PlatformConfig(
                    enabled=True,
                    token="xoxb-test",
                    home_channel=HomeChannel(
                        platform=Platform.SLACK,
                        chat_id="CLOG",
                        name="#로그",
                    ),
                )
            }
        )
        router = DeliveryRouter(config)

        targets = router.resolve_targets("slack")

        assert len(targets) == 1
        assert targets[0].platform == Platform.SLACK
        assert targets[0].chat_id == "CLOG"
        assert targets[0].thread_id is None

    def test_origin_preserves_thread_id(self):
        router = DeliveryRouter(GatewayConfig())
        origin = SessionSource(
            platform=Platform.SLACK,
            chat_id="C123",
            thread_id="171.001",
        )

        targets = router.resolve_targets("origin", origin=origin)

        assert len(targets) == 1
        assert targets[0].platform == Platform.SLACK
        assert targets[0].chat_id == "C123"
        assert targets[0].thread_id == "171.001"

    def test_mixed_targets_resolve_in_order(self):
        config = GatewayConfig(
            platforms={
                Platform.SLACK: PlatformConfig(
                    enabled=True,
                    token="xoxb-test",
                    home_channel=HomeChannel(
                        platform=Platform.SLACK,
                        chat_id="CLOG",
                        name="#로그",
                    ),
                )
            }
        )
        router = DeliveryRouter(config)

        targets = router.resolve_targets(["local", "slack:CALT", "slack"])

        assert [target.to_string() for target in targets] == [
            "local",
            "slack:CALT",
            "slack:CLOG",
        ]

import asyncio

from database import requests as r


def test_set_onboarded(make_user):
    make_user(tg_id=100, onboarded=False)
    asyncio.run(r.set_onboarded(100))
    assert asyncio.run(r.get_user(100)).onboarded is True


def test_new_user_is_not_onboarded(db):
    asyncio.run(r.set_user(200))
    user = asyncio.run(r.get_user(200))
    assert user.onboarded is False
    assert user.is_banned is False

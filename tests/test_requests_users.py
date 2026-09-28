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


from database.models import Reward, UserReward


def add_reward_to(db, user_id, name="Камуфляж №1") -> int:
    async def go():
        async with db() as session:
            reward = Reward(name=name, gift_link="https://x", price=1)
            session.add(reward)
            await session.flush()
            ur = UserReward(user_id=user_id, reward_id=reward.id)
            session.add(ur)
            await session.commit()
            return ur.id
    return asyncio.run(go())


def test_reward_status_toggle(db, make_user):
    uid = make_user(tg_id=400)
    ur_id = add_reward_to(db, uid)

    [(ur, reward)] = asyncio.run(r.get_user_rewards_with_status(uid))
    assert (ur.id, reward.name, ur.issued) == (ur_id, "Камуфляж №1", False)

    assert asyncio.run(r.toggle_reward_issued(ur_id)) == (True, 400, "Камуфляж №1")
    assert asyncio.run(r.toggle_reward_issued(ur_id)) == (False, 400, "Камуфляж №1")
    assert asyncio.run(r.toggle_reward_issued(9999)) is None


def test_set_banned(make_user):
    uid = make_user(tg_id=300)
    assert asyncio.run(r.set_banned(uid, True)) is True
    assert asyncio.run(r.get_user(300)).is_banned is True
    asyncio.run(r.set_banned(uid, False))
    assert asyncio.run(r.get_user(300)).is_banned is False
    assert asyncio.run(r.set_banned(9999, True)) is False


def test_get_admin_tg_ids(make_user):
    make_user(name="adm", tg_id=1, status="admin")
    make_user(name="usr", tg_id=2)
    assert asyncio.run(r.get_admin_tg_ids()) == [1]

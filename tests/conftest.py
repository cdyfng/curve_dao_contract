#!/usr/bin/python3

import pytest



YEAR = 365 * 86400
INITIAL_RATE = 274_815_283
YEAR_1_SUPPLY = INITIAL_RATE * 10 ** 18 // YEAR * YEAR
INITIAL_SUPPLY = 1_303_030_303

def approx(a, b, precision=1e-10):
    if a == b == 0:
        return True
    return 2 * abs(a - b) / (a + b) <= precision



def pack_values(values):
    packed = b"".join(i.to_bytes(1, "big") for i in values)
    padded = packed + bytes(32 - len(values))
    return padded

@pytest.fixture(autouse=True)
def isolation_setup(fn_isolation):
    pass


@pytest.fixture(scope="function", autouse=True)
def isolate(fn_isolation):
    # perform a chain rewind after completing each test, to ensure proper isolation
    # https://eth-brownie.readthedocs.io/en/v1.10.3/tests-pytest-intro.html#isolation-fixtures
    pass


# @pytest.fixture(scope="module")
# def token(Token, accounts):
#     return Token.deploy("Test Token", "TST", 18, 1e21, {'from': accounts[0]})


@pytest.fixture(scope="module")
def token(ERC20CRV, accounts):
    yield ERC20CRV.deploy("Curve DAO Token", "CRV", 18, {'from': accounts[0]})


@pytest.fixture(scope="module")
def voting_escrow(VotingEscrow, accounts, token):
    yield VotingEscrow.deploy(token, 'Voting-escrowed CRV', 'veCRV', 'veCRV_0.99', {'from': accounts[0]})


@pytest.fixture(scope="module")
def gauge_controller(GaugeController, accounts, token, voting_escrow):
    yield GaugeController.deploy(token, voting_escrow, {'from': accounts[0]})


@pytest.fixture(scope="module")
def minter(Minter, accounts, gauge_controller, token):
    yield Minter.deploy(token, gauge_controller, {'from': accounts[0]})


@pytest.fixture(scope="module")
def registry(Registry, accounts, susd_pool, mock_lp_token_susd):
    registry = Registry.deploy(["0x0000000000000000000000000000000000000000"] * 4, {'from': accounts[0]})
    registry.add_pool(
        susd_pool, 2, mock_lp_token_susd,
        "0x0000000000000000000000000000000000000000", "0x00",
        pack_values([18, 18]), pack_values([18, 18]),
        {'from': accounts[0]})

    yield registry


@pytest.fixture(scope="module")
def pool_proxy(PoolProxy, accounts, registry, susd_pool):
    proxy = PoolProxy.deploy(registry, accounts[0], accounts[0], accounts[0], {'from': accounts[0]})

    susd_pool.commit_transfer_ownership(proxy, {'from': accounts[0]})
    susd_pool.apply_transfer_ownership({'from': accounts[0]})

    return proxy


@pytest.fixture(scope="module")
def coin_reward(ERC20, accounts):
    yield ERC20.deploy("YFIIIIII Funance", "YFIIIIII", 18, {'from': accounts[0]})


@pytest.fixture(scope="module")
def reward_contract(CurveRewards, mock_lp_token, accounts, coin_reward):
    contract = CurveRewards.deploy(mock_lp_token, coin_reward, {'from': accounts[0]})
    contract.setRewardDistribution(accounts[0], {'from': accounts[0]})
    yield contract


@pytest.fixture(scope="module")
def liquidity_gauge(LiquidityGauge, accounts, mock_lp_token, minter):
    yield LiquidityGauge.deploy(mock_lp_token, minter, accounts[0], {'from': accounts[0]})


@pytest.fixture(scope="module")
def liquidity_gauge_reward(LiquidityGaugeReward, accounts, mock_lp_token, minter, reward_contract, coin_reward):
    yield LiquidityGaugeReward.deploy(mock_lp_token, minter, reward_contract, coin_reward, accounts[0], {'from': accounts[0]})


@pytest.fixture(scope="module")
def three_gauges(LiquidityGauge, accounts, mock_lp_token, minter):
    contracts = [
        LiquidityGauge.deploy(mock_lp_token, minter, accounts[0], {'from': accounts[0]})
        for _ in range(3)
    ]

    yield contracts


# VestingEscrow fixtures

@pytest.fixture(scope="module")
def start_time(chain):
    yield chain.time() + 1000 + 86400*365


@pytest.fixture(scope="module")
def end_time(start_time):
    yield start_time + 100000000


@pytest.fixture(scope="module")
def vesting(VestingEscrow, accounts, coin_a, start_time, end_time):
    contract = VestingEscrow.deploy(coin_a, start_time, end_time, True, accounts[1:5], {'from': accounts[0]})
    coin_a._mint_for_testing(10**21, {'from': accounts[0]})
    coin_a.approve(contract, 10**21, {'from': accounts[0]})
    yield contract


@pytest.fixture(scope="module")
def vesting_target(VestingEscrowSimple, accounts):
    yield VestingEscrowSimple.deploy({'from': accounts[0]})


@pytest.fixture(scope="module")
def vesting_factory(VestingEscrowFactory, accounts, vesting_target):
    yield VestingEscrowFactory.deploy(vesting_target, accounts[0], {'from': accounts[0]})


@pytest.fixture(scope="module")
def vesting_simple(VestingEscrowSimple, accounts, vesting_factory, coin_a, start_time):
    coin_a._mint_for_testing(10**21, {'from': accounts[0]})
    coin_a.transfer(vesting_factory, 10**21, {'from': accounts[0]})
    tx = vesting_factory.deploy_vesting_contract(
        coin_a, accounts[1], 10**20, True, 100000000, start_time, {'from': accounts[0]}
    )
    yield VestingEscrowSimple.at(tx.new_contracts[0])


# testing contracts

@pytest.fixture(scope="module")
def coin_a(ERC20, accounts):
    yield ERC20.deploy("Coin A", "USDA", 18, {'from': accounts[0]})


@pytest.fixture(scope="module")
def coin_b(ERC20, accounts):
    yield ERC20.deploy("Coin B", "USDB", 18, {'from': accounts[0]})


@pytest.fixture(scope="module")
def mock_lp_token(ERC20LP, accounts):  # Not using the actual Curve contract
    yield ERC20LP.deploy("Curve LP token", "usdCrv", 18, 10 ** 9, {'from': accounts[0]})

@pytest.fixture(scope="module")
def pool(CurvePool, accounts, mock_lp_token, coin_a, coin_b):
    curve_pool = CurvePool.deploy(
        [coin_a, coin_b], mock_lp_token, 100, 4 * 10 ** 6, {'from': accounts[0]}
    )
    mock_lp_token.set_minter(curve_pool, {'from': accounts[0]})

    yield curve_pool


@pytest.fixture(scope="module")
def mock_lp_token_susd(ERC20LP, accounts):
    yield ERC20LP.deploy("Curve LP token S", "susdCrv", 18, 0, {'from': accounts[0]})


@pytest.fixture(scope="module")
def susd_pool(StableSwapSUSD, accounts, mock_lp_token_susd, coin_a, coin_b):
    curve_pool = StableSwapSUSD.deploy(
        [coin_a, coin_b], [coin_a, coin_b], mock_lp_token_susd, 100, 4 * 10 ** 6, {'from': accounts[0]}
    )
    mock_lp_token_susd.set_minter(curve_pool, {'from': accounts[0]})

    coin_a._mint_for_testing(10**21, {'from': accounts[0]})
    coin_b._mint_for_testing(3 * 10**20, {'from': accounts[0]})
    coin_a.approve(curve_pool, 10**21, {'from': accounts[0]})
    coin_b.approve(curve_pool, 10**21, {'from': accounts[0]})
    # Deposit with asymmetry
    curve_pool.add_liquidity([10**21, 3 * 10**20], 0, {'from': accounts[0]})

    yield curve_pool


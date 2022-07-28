# ViewModel refers to json response structures
from typing import TypedDict, Optional

HYBRID_PAYMENT_MODE_BRFCID = "ef63d9775da5"


class PeerChannel(TypedDict):
    host: str
    token: str
    channelid: str


class PeerChannelsDPP(TypedDict):
    peerChannel: dict


class HybridPaymentModeStandardDPP(TypedDict):
    optionId: str
    transactions: list[str]
    ancestors: Optional[dict]


class HybridPaymentModeDPP(TypedDict):
    # i.e. { HYBRID_PAYMENT_MODE_BRFCID: HybridPaymentModeStandard }
    ef63d9775da5: HybridPaymentModeStandardDPP


class PaymentDPP(TypedDict):
    modeId: str  # i.e. HYBRID_PAYMENT_MODE_BRFCID
    mode: HybridPaymentModeDPP
    originator: Optional[dict]
    transaction: Optional[str]  # DEPRECATED as per TSC spec.
    memo: Optional[str]  # Optional


class PaymentTermsDPP(TypedDict):
    network: str
    version: str
    creationTimestamp: int
    expirationTimestamp: int
    memo: str
    paymentUrl: str
    beneficiary: dict
    modes: HybridPaymentModeDPP
    # for backwards compatibility:
    outputs: list
    merchantData: dict
    # for display in index.html only
    id: str
    state: int


class PaymentACK(TypedDict):
    modeId: str
    mode: HybridPaymentModeDPP
    peerChannel: PeerChannel
    redirectUrl: Optional[str]


class RetentionViewModel(TypedDict):
    min_age_days: int
    max_age_days: int
    auto_prune: bool


class PeerChannelAPITokenViewModelGet(TypedDict):
    id: int
    token: str
    description: str
    can_read: bool
    can_write: bool


class PeerChannelViewModelGet(TypedDict):
    id: str
    href: str
    public_read: bool
    public_write: bool
    sequenced: bool
    locked: bool
    head_sequence: int
    retention: RetentionViewModel
    access_tokens: list[PeerChannelAPITokenViewModelGet]
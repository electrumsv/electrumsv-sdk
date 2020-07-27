class Output {
    constructor(script, amount, description) {
        this.script = script;
        this.amount = amount;
        this.description = description;
    }
}

class PaymentRequest {
    constructor(creationTimestamp, expirationTimestamp, outputs, memo, paymentUrl, merchantData) {
        this.network = "bitcoin";
        this.creationTimestamp = creationTimestamp;
        this.expirationTimestamp = expirationTimestamp;
        this.outputs = outputs;
        this.memo = memo;
        this.paymentUrl = paymentUrl;
        this.merchantData = merchantData;
    }
}

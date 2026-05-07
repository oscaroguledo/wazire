"""Payment gateway integration: Paystack and Monnify.

Provides a unified ``PaymentGatewayService`` that abstracts over both gateways.
Routes and worker handlers call ``PaymentGatewayService.initiate(invoice)`` and
receive a normalised result regardless of which gateway is configured.
"""
from __future__ import annotations

import base64
from typing import Any, Dict, Optional

import httpx

from core.config import get_settings
from core.utils.logger import logger
from models.billings.invoice import Invoice


class PaymentGatewayError(Exception):
    """Raised when a payment gateway call fails."""


class PaymentGatewayResult:
    """Normalised result from a gateway initiation call."""

    def __init__(
        self,
        payment_url: Optional[str],
        payment_reference: Optional[str],
        gateway: str,
        raw: Dict[str, Any],
    ) -> None:
        self.payment_url = payment_url
        self.payment_reference = payment_reference
        self.gateway = gateway
        self.raw = raw


class PaymentGatewayService:
    """Unified payment gateway service supporting Paystack and Monnify.

    Usage::

        svc = PaymentGatewayService()
        result = await svc.initiate(invoice)
        # result.payment_url  → redirect URL for the tenant admin
        # result.payment_reference  → reference to store on Invoice
    """

    PAYSTACK_INIT_URL = "https://api.paystack.co/transaction/initialize"
    MONNIFY_AUTH_URL = "https://sandbox.monnify.com/api/v1/auth/login"
    MONNIFY_INIT_URL = "https://sandbox.monnify.com/api/v1/merchant/transactions/init-transaction"

    def __init__(self) -> None:
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def initiate(self, invoice: Invoice) -> PaymentGatewayResult:
        """Initiate a payment for the given invoice.

        Selects the gateway based on ``invoice.payment_gateway`` if set,
        otherwise falls back to Paystack if ``PAYSTACK_SECRET_KEY`` is
        configured, then Monnify.

        Raises:
            PaymentGatewayError: if no gateway is configured or the API call fails.
        """
        gateway = (invoice.payment_gateway or "").lower()

        if gateway == "monnify" or (not gateway and not self._settings.PAYSTACK_SECRET_KEY):
            return await self._initiate_monnify(invoice)

        # Default: Paystack
        return await self._initiate_paystack(invoice)

    # ------------------------------------------------------------------
    # Paystack
    # ------------------------------------------------------------------

    async def _initiate_paystack(self, invoice: Invoice) -> PaymentGatewayResult:
        """Call Paystack transaction/initialize and return a normalised result."""
        secret_key = self._settings.PAYSTACK_SECRET_KEY
        if not secret_key:
            raise PaymentGatewayError("PAYSTACK_SECRET_KEY is not configured")

        # Paystack expects amount in kobo (1 NGN = 100 kobo)
        amount_kobo = invoice.total_amount * 100

        payload: Dict[str, Any] = {
            "amount": amount_kobo,
            "currency": "NGN",
            "metadata": {
                "invoice_id": str(invoice.id),
                "tenant_id": str(invoice.tenant_id),
                "description": invoice.description,
            },
        }

        # Use tenant's Paystack customer code if available
        if hasattr(invoice, "tenant") and invoice.tenant and getattr(invoice.tenant, "paystack_customer_code", None):
            payload["customer"] = invoice.tenant.paystack_customer_code

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.PAYSTACK_INIT_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {secret_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Paystack initiate failed (invoice=%s status=%d): %s",
                invoice.id, exc.response.status_code, exc.response.text,
            )
            raise PaymentGatewayError(f"Paystack API error: {exc.response.status_code}") from exc
        except Exception as exc:
            logger.exception("Paystack initiate request failed (invoice=%s)", invoice.id)
            raise PaymentGatewayError(f"Paystack request failed: {exc}") from exc

        if not data.get("status"):
            raise PaymentGatewayError(f"Paystack returned status=false: {data.get('message')}")

        tx_data = data.get("data", {})
        return PaymentGatewayResult(
            payment_url=tx_data.get("authorization_url"),
            payment_reference=tx_data.get("reference"),
            gateway="paystack",
            raw=data,
        )

    # ------------------------------------------------------------------
    # Monnify
    # ------------------------------------------------------------------

    async def _get_monnify_token(self) -> str:
        """Authenticate with Monnify and return a bearer token."""
        api_key = self._settings.MONNIFY_API_KEY
        secret_key = self._settings.MONNIFY_SECRET_KEY
        if not api_key or not secret_key:
            raise PaymentGatewayError("MONNIFY_API_KEY and MONNIFY_SECRET_KEY are not configured")

        credentials = base64.b64encode(f"{api_key}:{secret_key}".encode()).decode()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.MONNIFY_AUTH_URL,
                    headers={"Authorization": f"Basic {credentials}"},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise PaymentGatewayError(f"Monnify auth error: {exc.response.status_code}") from exc
        except Exception as exc:
            raise PaymentGatewayError(f"Monnify auth request failed: {exc}") from exc

        token = data.get("responseBody", {}).get("accessToken")
        if not token:
            raise PaymentGatewayError("Monnify auth did not return an accessToken")
        return token

    async def _initiate_monnify(self, invoice: Invoice) -> PaymentGatewayResult:
        """Call Monnify init-transaction and return a normalised result."""
        token = await self._get_monnify_token()

        payload: Dict[str, Any] = {
            "amount": invoice.total_amount,
            "customerName": str(invoice.tenant_id),
            "customerEmail": f"billing+{invoice.tenant_id}@wazire.com",
            "paymentReference": str(invoice.id),
            "paymentDescription": invoice.description,
            "currencyCode": "NGN",
            "contractCode": self._settings.MONNIFY_API_KEY or "",
            "redirectUrl": f"{self._settings.FRONTEND_URL}/billing/invoices/{invoice.id}",
            "paymentMethods": ["ACCOUNT_TRANSFER", "CARD"],
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self.MONNIFY_INIT_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Monnify initiate failed (invoice=%s status=%d): %s",
                invoice.id, exc.response.status_code, exc.response.text,
            )
            raise PaymentGatewayError(f"Monnify API error: {exc.response.status_code}") from exc
        except Exception as exc:
            logger.exception("Monnify initiate request failed (invoice=%s)", invoice.id)
            raise PaymentGatewayError(f"Monnify request failed: {exc}") from exc

        body = data.get("responseBody", {})
        return PaymentGatewayResult(
            payment_url=body.get("checkoutUrl"),
            payment_reference=body.get("transactionReference"),
            gateway="monnify",
            raw=data,
        )

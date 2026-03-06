"""Notification service -- email sending (SMTP) and in-app notifications.

Templates:
- pedido_enviado
- pedido_aprobado
- pedido_rechazado
- devolucion_registrada
- comision_calculada
"""

from __future__ import annotations


import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.exceptions import NotFoundException
from api.db.models.notification import NotificationModel
from api.models.notification import (
    EmailTemplateResponse,
    NotificationResponse,
    UnreadCountResponse,
)

logger = logging.getLogger("bonapharm.notification_service")

# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------

EMAIL_TEMPLATES: dict[str, dict[str, str]] = {
    "pedido_enviado": {
        "nombre": "Pedido Enviado",
        "asunto": "Su pedido {codigo_pedido} ha sido enviado y esta en revision",
        "body": (
            "Estimado/a {vendedor_nombre},\n\n"
            "Su pedido {codigo_pedido} ha sido enviado exitosamente y "
            "se encuentra en proceso de revision.\n\n"
            "Total: S/ {total}\n\nSaludos,\nBONAPHARM"
        ),
        "variables": "codigo_pedido,vendedor_nombre,total",
    },
    "pedido_aprobado": {
        "nombre": "Pedido Aprobado",
        "asunto": "Su pedido {codigo_pedido} ha sido aprobado por {aprobador_nombre}",
        "body": (
            "Estimado/a {vendedor_nombre},\n\n"
            "Su pedido {codigo_pedido} ha sido aprobado por {aprobador_nombre}.\n\n"
            "Saludos,\nBONAPHARM"
        ),
        "variables": "codigo_pedido,vendedor_nombre,aprobador_nombre",
    },
    "pedido_rechazado": {
        "nombre": "Pedido Rechazado",
        "asunto": "Su pedido {codigo_pedido} fue rechazado",
        "body": (
            "Estimado/a {vendedor_nombre},\n\n"
            "Su pedido {codigo_pedido} fue rechazado.\n"
            "Motivo: {motivo_rechazo}\n\n"
            "Saludos,\nBONAPHARM"
        ),
        "variables": "codigo_pedido,vendedor_nombre,motivo_rechazo",
    },
    "devolucion_registrada": {
        "nombre": "Devolucion Registrada",
        "asunto": "Devolucion {codigo_devolucion} registrada y en proceso de revision",
        "body": (
            "Se ha registrado la devolucion {codigo_devolucion} "
            "y se encuentra en proceso de revision.\n\n"
            "Saludos,\nBONAPHARM"
        ),
        "variables": "codigo_devolucion",
    },
    "comision_calculada": {
        "nombre": "Comision Calculada",
        "asunto": "Comision del mes {mes}/{anio} calculada: S/ {neto_a_pagar}",
        "body": (
            "Se ha calculado la comision del periodo {mes}/{anio}.\n"
            "Neto a pagar: S/ {neto_a_pagar}\n\n"
            "Saludos,\nBONAPHARM"
        ),
        "variables": "mes,anio,neto_a_pagar",
    },
}


class NotificationService:
    """Manages in-app notifications and email dispatch."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # In-app notifications
    # ------------------------------------------------------------------

    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> list[NotificationResponse]:
        """List notifications for a user."""
        stmt = (
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [NotificationResponse.model_validate(r) for r in rows]

    async def mark_as_read(self, notification_id: uuid.UUID) -> NotificationResponse:
        """Mark a single notification as read."""
        notif = await self.session.get(NotificationModel, notification_id)
        if not notif:
            raise NotFoundException("Notificacion", str(notification_id))
        notif.leido = True
        await self.session.commit()
        await self.session.refresh(notif)
        return NotificationResponse.model_validate(notif)

    async def delete(self, notification_id: uuid.UUID) -> None:
        """Delete a notification."""
        notif = await self.session.get(NotificationModel, notification_id)
        if not notif:
            raise NotFoundException("Notificacion", str(notification_id))
        await self.session.delete(notif)
        await self.session.commit()

    async def unread_count(self, user_id: uuid.UUID) -> UnreadCountResponse:
        """Count unread notifications for a user."""
        stmt = (
            select(func.count())
            .select_from(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.leido == False,  # noqa: E712
            )
        )
        result = await self.session.execute(stmt)
        return UnreadCountResponse(count=result.scalar_one())

    async def create_notification(
        self,
        user_id: uuid.UUID,
        titulo: str,
        mensaje: str,
        tipo: str = "InApp",
        entidad: Optional[str] = None,
        entidad_id: Optional[uuid.UUID] = None,
    ) -> NotificationModel:
        """Create and persist an in-app notification."""
        notif = NotificationModel(
            user_id=user_id,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            entidad=entidad,
            entidad_id=entidad_id,
        )
        self.session.add(notif)
        await self.session.commit()
        await self.session.refresh(notif)
        return notif

    # ------------------------------------------------------------------
    # Sent history
    # ------------------------------------------------------------------

    async def get_sent_history(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> list[NotificationResponse]:
        """List sent notifications (email)."""
        stmt = (
            select(NotificationModel)
            .where(NotificationModel.enviado == True)  # noqa: E712
            .order_by(NotificationModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [NotificationResponse.model_validate(r) for r in rows]

    # ------------------------------------------------------------------
    # Email sending
    # ------------------------------------------------------------------

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        user_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """Send an email via SMTP. Returns True on success.

        In development mode or when SMTP is not configured, the email
        is logged but not actually sent.
        """
        if not settings.SMTP_HOST or settings.ENVIRONMENT == "development":
            logger.info(
                "Email (dev mode, not sent): to=%s subject=%s", to, subject
            )
            # Persist as notification for audit trail
            if user_id:
                await self.create_notification(
                    user_id=user_id,
                    titulo=subject,
                    mensaje=body,
                    tipo="Email",
                )
            return True

        try:
            import aiosmtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["From"] = settings.SMTP_FROM_EMAIL
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(body)

            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER or None,
                password=settings.SMTP_PASSWORD or None,
                use_tls=settings.SMTP_TLS,
            )

            if user_id:
                notif = await self.create_notification(
                    user_id=user_id,
                    titulo=subject,
                    mensaje=body,
                    tipo="Email",
                )
                notif.enviado = True
                notif.fecha_envio = datetime.now(timezone.utc)
                await self.session.commit()

            logger.info("Email sent: to=%s subject=%s", to, subject)
            return True

        except Exception:
            logger.exception("Failed to send email to %s", to)
            return False

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    @staticmethod
    def list_templates() -> list[EmailTemplateResponse]:
        """Return all available email templates."""
        return [
            EmailTemplateResponse(
                id=key,
                nombre=val["nombre"],
                asunto=val["asunto"],
                variables=val["variables"].split(","),
            )
            for key, val in EMAIL_TEMPLATES.items()
        ]

# repositories/client_repository.py - FIXED FIELD MAPPING

"""Client repository for simplified grid trading service - FIXED MAPPING"""

import logging
import sqlite3
from datetime import datetime
from typing import Optional

from config import Config
from models.client import Client, ClientStatus, GridStatus
from utils.crypto import CryptoUtils


class ClientRepository:
    """Repository for client data management - FIXED FIELD MAPPING"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.crypto_utils = CryptoUtils()
        self.logger = logging.getLogger(__name__)

    def create_client(
        self, telegram_id: int, username: str = None, first_name: str = None
    ) -> Client:
        """Create a new client"""
        client = Client(
            telegram_id=telegram_id, username=username, first_name=first_name
        )

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO clients (
                        telegram_id, username, first_name, status, 
                        grid_status, created_at, total_capital, risk_level,
                        trading_pairs, grid_spacing, grid_levels, order_size
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        client.telegram_id,
                        client.username,
                        client.first_name,
                        client.status.value,
                        client.grid_status.value,
                        client.created_at.isoformat(),
                        client.total_capital,
                        client.risk_level,
                        ",".join(client.trading_pairs),
                        client.grid_spacing,
                        client.grid_levels,
                        client.order_size,
                    ),
                )

            self.logger.info(f"Created client: {telegram_id}")
            return client

        except sqlite3.IntegrityError:
            # Client already exists, return existing client
            return self.get_client(telegram_id)
        except Exception as e:
            self.logger.error(f"Error creating client {telegram_id}: {e}")
            return client

    def get_client(self, telegram_id: int) -> Optional[Client]:
        """Get client by telegram ID - FIXED FIELD MAPPING"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT telegram_id, username, first_name, status, grid_status,
                           created_at, updated_at, total_capital, risk_level,
                           trading_pairs, binance_api_key, binance_secret_key,
                           grid_spacing, grid_levels, order_size
                    FROM clients WHERE telegram_id = ?
                """,
                    (telegram_id,),
                )

                row = cursor.fetchone()
                if not row:
                    self.logger.warning(f"Client {telegram_id} not found in database")
                    return None

                self.logger.debug(
                    f"Retrieved client data for {telegram_id}: {len(row)} fields"
                )

                # FIXED: Correct field mapping with proper indexes
                try:
                    client_data = {
                        "telegram_id": row[0],  # 0
                        "username": row[1],  # 1
                        "first_name": row[2],  # 2
                        "status": ClientStatus(row[3])
                        if row[3]
                        else ClientStatus.ACTIVE,  # 3
                        "grid_status": GridStatus(row[4])
                        if row[4]
                        else GridStatus.INACTIVE,  # 4
                        "total_capital": float(row[7])
                        if row[7] is not None
                        else 0.0,  # 7
                        "risk_level": row[8] if row[8] else "moderate",  # 8
                        "grid_spacing": float(row[12])
                        if row[12] is not None
                        else 0.025,  # 12
                        "grid_levels": int(row[13]) if row[13] is not None else 8,  # 13
                        "order_size": float(row[14])
                        if row[14] is not None
                        else 50.0,  # 14
                    }

                    # Parse datetime fields safely
                    # created_at (index 5)
                    if row[5]:
                        try:
                            client_data["created_at"] = datetime.fromisoformat(row[5])
                        except:
                            client_data["created_at"] = datetime.now()
                    else:
                        client_data["created_at"] = datetime.now()

                    # updated_at (index 6)
                    if row[6]:
                        try:
                            client_data["updated_at"] = datetime.fromisoformat(row[6])
                        except:
                            client_data["updated_at"] = datetime.now()
                    else:
                        client_data["updated_at"] = datetime.now()

                    # Parse trading pairs (index 9)
                    if row[9]:
                        client_data["trading_pairs"] = row[9].split(",")
                    else:
                        client_data["trading_pairs"] = ["ADA", "AVAX"]

                    # Handle encrypted API keys (indexes 10, 11)
                    client_data["binance_api_key"] = row[10]  # Keep encrypted
                    client_data["binance_secret_key"] = row[11]  # Keep encrypted

                    self.logger.debug(
                        f"Client data parsed successfully for {telegram_id}"
                    )
                    return Client(**client_data)

                except (ValueError, TypeError, IndexError) as parse_error:
                    self.logger.error(
                        f"Error parsing client data for {telegram_id}: {parse_error}"
                    )
                    self.logger.error(f"Row data: {row}")
                    return None

        except Exception as e:
            self.logger.error(f"Error getting client {telegram_id}: {e}")
            return None

    def get_decrypted_api_keys(self, client: Client) -> tuple:
        """Get decrypted API keys for a client"""
        try:
            if not client.binance_api_key or not client.binance_secret_key:
                self.logger.debug(
                    f"No API keys to decrypt for client {client.telegram_id}"
                )
                return None, None

            self.logger.debug(f"Decrypting API keys for client {client.telegram_id}")
            api_key = self.crypto_utils.decrypt(client.binance_api_key)
            secret_key = self.crypto_utils.decrypt(client.binance_secret_key)

            self.logger.debug(
                f"Successfully decrypted API keys for client {client.telegram_id}"
            )
            return api_key, secret_key

        except Exception as e:
            self.logger.error(
                f"Error decrypting API keys for client {client.telegram_id}: {e}"
            )
            return None, None

    def update_client(self, client: Client) -> bool:
        """Update client information"""
        try:
            # Encrypt API keys before storing if they're not already encrypted
            encrypted_api_key = None
            encrypted_secret_key = None

            if client.binance_api_key:
                # Check if it's already encrypted (long base64 string)
                if len(client.binance_api_key) > 100:
                    # Already encrypted
                    encrypted_api_key = client.binance_api_key
                    self.logger.debug(
                        f"API key for client {client.telegram_id} appears to be already encrypted"
                    )
                else:
                    # Raw key, needs encryption
                    encrypted_api_key = self.crypto_utils.encrypt(
                        client.binance_api_key
                    )
                    self.logger.debug(
                        f"Encrypting raw API key for client {client.telegram_id}"
                    )

            if client.binance_secret_key:
                # Check if it's already encrypted (long base64 string)
                if len(client.binance_secret_key) > 100:
                    # Already encrypted
                    encrypted_secret_key = client.binance_secret_key
                    self.logger.debug(
                        f"Secret key for client {client.telegram_id} appears to be already encrypted"
                    )
                else:
                    # Raw key, needs encryption
                    encrypted_secret_key = self.crypto_utils.encrypt(
                        client.binance_secret_key
                    )
                    self.logger.debug(
                        f"Encrypting raw secret key for client {client.telegram_id}"
                    )

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE clients SET
                        username = ?, first_name = ?, status = ?, grid_status = ?,
                        total_capital = ?, risk_level = ?, trading_pairs = ?,
                        binance_api_key = ?, binance_secret_key = ?,
                        grid_spacing = ?, grid_levels = ?, order_size = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE telegram_id = ?
                """,
                    (
                        client.username,
                        client.first_name,
                        client.status.value,
                        client.grid_status.value,
                        client.total_capital,
                        client.risk_level,
                        ",".join(client.trading_pairs),
                        encrypted_api_key,
                        encrypted_secret_key,
                        client.grid_spacing,
                        client.grid_levels,
                        client.order_size,
                        client.telegram_id,
                    ),
                )

            self.logger.info(f"Updated client {client.telegram_id} successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error updating client {client.telegram_id}: {e}")
            return False

    def get_all_active_clients(self) -> list:
        """Get all active clients"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT telegram_id FROM clients 
                    WHERE status = ? AND binance_api_key IS NOT NULL
                """,
                    (ClientStatus.ACTIVE.value,),
                )

                return [row[0] for row in cursor.fetchall()]

        except Exception as e:
            self.logger.error(f"Error getting active clients: {e}")
            return []

    def client_exists(self, telegram_id: int) -> bool:
        """Check if client exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM clients WHERE telegram_id = ?", (telegram_id,)
                )
                return cursor.fetchone() is not None
        except:
            return False

    def debug_client_data(self, telegram_id: int):
        """Debug method to check client data structure"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get column names
                cursor = conn.execute("PRAGMA table_info(clients)")
                columns = [(row[1], row[2]) for row in cursor.fetchall()]

                self.logger.info(f"Client table columns: {columns}")

                # Get client data
                cursor = conn.execute(
                    "SELECT * FROM clients WHERE telegram_id = ?", (telegram_id,)
                )
                row = cursor.fetchone()

                if row:
                    self.logger.info(f"Client {telegram_id} data length: {len(row)}")
                    for i, value in enumerate(row):
                        if i < len(columns):
                            col_name = columns[i][0]
                            self.logger.info(
                                f"  {i}: {col_name} = {str(value)[:50]}..."
                            )
                else:
                    self.logger.info(f"No data found for client {telegram_id}")

        except Exception as e:
            self.logger.error(f"Debug error: {e}")

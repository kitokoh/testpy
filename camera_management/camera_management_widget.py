# -*- coding: utf-8 -*-
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QLabel,
    QDialog, QFormLayout, QLineEdit, QMessageBox, QDialogButtonBox,
    QListWidgetItem, QMenu
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

# Assuming db_manager and company_assets_crud are accessible.
# These imports might need adjustment based on the final project structure
# and how global instances or accessors are defined.
# from .. import db as db_manager # Example if db is one level up
from db.cruds.company_assets_crud import company_assets_crud
# from db.cruds.users_crud import users_crud # If needed for created_by_user_id

logger = logging.getLogger(__name__)

class AddEditCameraDialog(QDialog):
    """
    A dialog for adding a new camera or editing an existing one.
    It collects camera details such as name, description, stream URL, and other notes.
    The stream URL and other notes are currently stored combined in the 'notes' field
    of the CompanyAsset.
    """
    def __init__(self, parent=None, camera_asset=None, current_user_id=None):
        super().__init__(parent)
        self.camera_asset = camera_asset
        self.current_user_id = current_user_id # Will be used when saving

        self.setWindowTitle(self.tr("Modifier Caméra") if camera_asset else self.tr("Ajouter Caméra"))
        # self.setWindowIcon(QIcon(":/icons/camera.svg")) # Placeholder for a camera icon

        layout = QFormLayout(self)

        self.name_edit = QLineEdit(self)
        self.description_edit = QLineEdit(self) # For location, etc.
        self.stream_url_edit = QLineEdit(self)
        self.other_notes_edit = QLineEdit(self)

        layout.addRow(self.tr("Nom Caméra:"), self.name_edit)
        layout.addRow(self.tr("Description (Lieu, etc.):"), self.description_edit)
        layout.addRow(self.tr("URL du Flux (RTSP/HTTP):"), self.stream_url_edit)
        layout.addRow(self.tr("Autres Notes (IP, modèle, etc.):"), self.other_notes_edit)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        if self.camera_asset:
            self._load_camera_data()

    def _load_camera_data(self):
        self.name_edit.setText(self.camera_asset.get('asset_name', ''))
        self.description_edit.setText(self.camera_asset.get('description', ''))

        notes_content = self.camera_asset.get('notes', '')
        # V1 Design Choice: Storing stream URL and other notes in the 'notes' field.
        # The stream URL is separated from other notes by ';;STREAM_URL_SEP;;'.
        # This is a simplified approach. Future improvements could involve:
        #   - Dedicated database fields for stream_url, ip_address, model, etc.
        #   - Using an AssetMediaLink table if multiple streams or media are associated with one asset.
        # CAUTION: Avoid storing sensitive credentials (e.g., RTSP username/password) directly
        # in these fields due to security risks. Consider safer credential management strategies
        # if authentication is required for streams.
        parts = notes_content.split(';;STREAM_URL_SEP;;', 1)
        stream_url = parts[0] if parts else ''
        other_notes = parts[1] if len(parts) > 1 else ''

        self.stream_url_edit.setText(stream_url)
        self.other_notes_edit.setText(other_notes)

    def get_data(self):
        # V1 Design Choice: Combine stream_url and other_notes into the 'notes' field
        # using ';;STREAM_URL_SEP;;' as a separator.
        # This is a simplified approach for V1. See notes in _load_camera_data for future improvements.
        # CAUTION: Ensure sensitive credentials are not stored here.
        notes_data = f"{self.stream_url_edit.text().strip()};;STREAM_URL_SEP;;{self.other_notes_edit.text().strip()}"

        data = {
            'asset_name': self.name_edit.text().strip(),
            'asset_type': 'Camera', # Fixed type
            'description': self.description_edit.text().strip(),
            'notes': notes_data,
            'current_status': self.camera_asset.get('current_status', 'Active') if self.camera_asset else 'Active', # Preserve status or default
        }
        # If editing, include asset_id for the update operation
        if self.camera_asset and self.camera_asset.get('asset_id'):
            data['asset_id'] = self.camera_asset['asset_id']
        return data

    def accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, self.tr("Validation"), self.tr("Le nom de la caméra ne peut pas être vide."))
            return
        if not self.stream_url_edit.text().strip():
            # Potentially validate URL format here too
            QMessageBox.warning(self, self.tr("Validation"), self.tr("L'URL du flux ne peut pas être vide."))
            return
        super().accept()


class CameraManagementWidget(QWidget):
    """
    A QWidget for managing and viewing camera streams.

    Module Usage:
    - To enable this module, go to Application Settings -> Gestion des Modules and activate "Camera Management".
      A restart might be required.
    - Cameras are stored as 'CompanyAsset' records with 'asset_type' = 'Camera'.
    - Basic functionality includes:
        - Listing available cameras.
        - Adding new cameras (name, description, stream URL, other notes).
        - Editing existing camera details.
        - Removing (archiving) cameras.
        - Selecting a camera from the list to view its video stream.
    - The stream URL is crucial for playback. Other notes can store details like IP, model, etc.
    """
    def __init__(self, parent=None, current_user_id=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.player = None

        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5,5,5,5) # Reduced margins

        # Left pane: Camera list and controls
        left_pane_widget = QWidget()
        left_pane_layout = QVBoxLayout(left_pane_widget)
        left_pane_layout.setContentsMargins(0,0,0,0)

        self.camera_list_widget = QListWidget()
        self.camera_list_widget.itemClicked.connect(self._on_camera_selected_from_list)
        self.camera_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.camera_list_widget.customContextMenuRequested.connect(self._show_camera_context_menu)

        left_pane_layout.addWidget(QLabel(self.tr("Caméras:")))
        left_pane_layout.addWidget(self.camera_list_widget)

        add_button_layout = QHBoxLayout() # Layout for the add button
        self.add_camera_button = QPushButton(QIcon(":/icons/plus-circle.svg"), self.tr("Ajouter Caméra")) # Icon from existing set
        self.add_camera_button.clicked.connect(self._add_camera_dialog)
        add_button_layout.addWidget(self.add_camera_button)
        left_pane_layout.addLayout(add_button_layout)

        left_pane_widget.setFixedWidth(250) # Fixed width for the camera list panel

        # Right pane: Video display
        right_pane_widget = QWidget()
        right_pane_layout = QVBoxLayout(right_pane_widget)
        right_pane_layout.setContentsMargins(0,0,0,0)

        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black;")

        self.video_placeholder_label = QLabel(self.tr("Sélectionnez une caméra pour afficher le flux vidéo."))
        self.video_placeholder_label.setAlignment(Qt.AlignCenter)
        self.video_placeholder_label.setStyleSheet("color: grey; font-size: 18px; background-color: black;")

        # Stack to switch between video and placeholder
        self.video_display_stack = QWidget()
        video_display_layout = QVBoxLayout(self.video_display_stack) # Use QVBoxLayout to manage single widget visibility
        video_display_layout.setContentsMargins(0,0,0,0)
        video_display_layout.addWidget(self.video_widget)
        video_display_layout.addWidget(self.video_placeholder_label)

        self.video_widget.setVisible(False) # Video hidden initially
        self.video_placeholder_label.setVisible(True) # Placeholder visible

        right_pane_layout.addWidget(self.video_display_stack)

        main_layout.addWidget(left_pane_widget)
        main_layout.addWidget(right_pane_widget, 1) # Video pane takes more space

        self._setup_media_player()
        self._load_cameras_from_db()

    def _setup_media_player(self):
        # QMediaPlayer is used for video playback.
        # Note: QMediaPlayer's support for various stream protocols (especially RTSP) can be
        # platform-dependent and sometimes limited. For robust RTSP support and wider codec
        # compatibility, alternative multimedia frameworks like VLC (python-vlc) or
        # GStreamer (PyGObject) might be considered in future versions if QMediaPlayer
        # proves insufficient for common camera stream types.
        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.video_widget)
        self.player.mediaStatusChanged.connect(self._handle_media_status_change)
        self.player.error.connect(self._handle_player_error)

    def _load_cameras_from_db(self):
        self.camera_list_widget.clear()
        try:
            camera_assets = company_assets_crud.get_assets(filters={'asset_type': 'Camera', 'is_deleted': 0})
            if not camera_assets:
                logger.info("No active camera assets found.")
                # Optionally show a message in the list or placeholder
            for asset in camera_assets:
                item = QListWidgetItem(asset.get('asset_name', self.tr("Caméra Sans Nom")))
                item.setData(Qt.UserRole, asset)
                self.camera_list_widget.addItem(item)
        except Exception as e:
            logger.error(f"Erreur lors du chargement des caméras: {e}", exc_info=True)
            QMessageBox.critical(self, self.tr("Erreur de Chargement"), self.tr("Impossible de charger la liste des caméras."))

    def _on_camera_selected_from_list(self, item):
        camera_asset = item.data(Qt.UserRole)
        if camera_asset:
            notes = camera_asset.get('notes', '')
            stream_url_str = notes.split(';;STREAM_URL_SEP;;', 1)[0].strip()

            if stream_url_str:
                logger.info(f"Tentative de lecture du flux: {stream_url_str}")
                self.video_placeholder_label.setText(self.tr("Chargement du flux..."))
                self.video_widget.setVisible(False)
                self.video_placeholder_label.setVisible(True)

                self.player.setMedia(QMediaContent(QUrl(stream_url_str)))
                self.player.play()
            else:
                logger.warning(f"Aucune URL de flux pour la caméra: {camera_asset.get('asset_name')}")
                self._stop_and_reset_player(self.tr("URL de flux non configurée."))
                QMessageBox.information(self, self.tr("Information"), self.tr("URL de flux non configurée pour cette caméra."))

    def _stop_and_reset_player(self, placeholder_message=None):
        if self.player:
            self.player.stop()
        self.video_widget.setVisible(False)
        self.video_placeholder_label.setText(placeholder_message or self.tr("Sélectionnez une caméra pour afficher le flux vidéo."))
        self.video_placeholder_label.setVisible(True)

    def _handle_media_status_change(self, status):
        logger.debug(f"Statut Média Modifié: {status}")
        if status == QMediaPlayer.LoadingMedia:
            self.video_placeholder_label.setText(self.tr("Chargement du flux..."))
            self.video_widget.setVisible(False)
            self.video_placeholder_label.setVisible(True)
        elif status == QMediaPlayer.LoadedMedia:
            self.video_widget.setVisible(True)
            self.video_placeholder_label.setVisible(False)
            self.player.play() # Ensure play starts once loaded
        elif status == QMediaPlayer.EndOfMedia:
            logger.info("Fin du média.")
            self._stop_and_reset_player(self.tr("Flux terminé ou déconnecté."))
        elif status == QMediaPlayer.InvalidMedia:
            logger.error("Média invalide.")
            self._stop_and_reset_player(self.tr("Média invalide ou URL de flux incorrecte."))
        elif status == QMediaPlayer.NoMedia:
             self._stop_and_reset_player(self.tr("Pas de média. Sélectionnez une caméra."))


    def _handle_player_error(self, error_code):
        error_string = self.player.errorString()
        logger.error(f"Erreur Lecteur ({error_code}): {error_string}")
        self._stop_and_reset_player(self.tr("Erreur Lecteur: {0}").format(error_string if error_string else self.tr("Inconnue")))
        # QMessageBox.warning(self, self.tr("Erreur Lecteur"), self.tr("Erreur: {0}").format(error_string)) # Can be too intrusive

    def _add_camera_dialog(self):
        if not self.current_user_id: # Assuming current_user_id is passed from main_window
            QMessageBox.critical(self, self.tr("Erreur Utilisateur"), self.tr("ID utilisateur non défini. Impossible d'ajouter."))
            return

        dialog = AddEditCameraDialog(parent=self, current_user_id=self.current_user_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            data['created_by_user_id'] = self.current_user_id

            try:
                asset_id = company_assets_crud.add_asset(data)
                if asset_id:
                    logger.info(f"Caméra ajoutée avec ID: {asset_id}")
                    self._load_cameras_from_db()
                    self._notify_main_window(self.tr("Succès"), self.tr("Caméra '{0}' ajoutée.").format(data['asset_name']), 'SUCCESS')
                else:
                    logger.error("Échec de l'ajout de la caméra, add_asset a retourné None.")
                    QMessageBox.critical(self, self.tr("Erreur Base de Données"), self.tr("Impossible d'ajouter la caméra."))
            except Exception as e:
                logger.error(f"Exception lors de l'ajout de la caméra: {e}", exc_info=True)
                QMessageBox.critical(self, self.tr("Erreur Exception"), self.tr("Exception: {0}").format(e))

    def _edit_camera_dialog(self, camera_asset_to_edit):
        if not camera_asset_to_edit:
            QMessageBox.information(self, self.tr("Sélection"), self.tr("Aucune caméra sélectionnée pour modification."))
            return

        dialog = AddEditCameraDialog(parent=self, camera_asset=camera_asset_to_edit, current_user_id=self.current_user_id)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            # data['updated_by_user_id'] = self.current_user_id # If model supports it

            try:
                success = company_assets_crud.update_asset(camera_asset_to_edit['asset_id'], data)
                if success:
                    logger.info(f"Caméra mise à jour: {camera_asset_to_edit['asset_id']}")
                    self._load_cameras_from_db()
                    self._notify_main_window(self.tr("Succès"), self.tr("Caméra '{0}' mise à jour.").format(data['asset_name']), 'SUCCESS')
                else:
                    logger.error(f"Échec de la mise à jour de la caméra: {camera_asset_to_edit['asset_id']}")
                    QMessageBox.critical(self, self.tr("Erreur Base de Données"), self.tr("Impossible de mettre à jour la caméra."))
            except Exception as e:
                logger.error(f"Exception lors de la mise à jour: {e}", exc_info=True)
                QMessageBox.critical(self, self.tr("Erreur Exception"), self.tr("Exception: {0}").format(e))

    def _remove_camera_logic(self, camera_asset_to_delete):
        if not camera_asset_to_delete:
            QMessageBox.information(self, self.tr("Sélection"), self.tr("Aucune caméra sélectionnée pour suppression."))
            return

        confirm = QMessageBox.question(self, self.tr("Confirmation"),
                                       self.tr("Supprimer la caméra '{0}'? (Archivage)").format(camera_asset_to_delete.get('asset_name')),
                                       QMessageBox.Yes | QMessageBox.No)
        if confirm == QMessageBox.Yes:
            try:
                success = company_assets_crud.delete_asset(camera_asset_to_delete['asset_id']) # Soft delete
                if success:
                    logger.info(f"Caméra archivée: {camera_asset_to_delete['asset_id']}")
                    self._load_cameras_from_db()
                    self._stop_and_reset_player()
                    self._notify_main_window(self.tr("Succès"), self.tr("Caméra '{0}' archivée.").format(camera_asset_to_delete.get('asset_name')), 'SUCCESS')
                else:
                    logger.error(f"Échec de l'archivage: {camera_asset_to_delete['asset_id']}")
                    QMessageBox.critical(self, self.tr("Erreur Base de Données"), self.tr("Impossible d'archiver la caméra."))
            except Exception as e:
                logger.error(f"Exception lors de l'archivage: {e}", exc_info=True)
                QMessageBox.critical(self, self.tr("Erreur Exception"), self.tr("Exception: {0}").format(e))

    def _show_camera_context_menu(self, pos):
        item = self.camera_list_widget.itemAt(pos)
        if not item: return
        camera_asset = item.data(Qt.UserRole)
        if not camera_asset: return

        menu = QMenu()
        edit_action = menu.addAction(QIcon(":/icons/pencil.svg"), self.tr("Modifier"))
        edit_action.triggered.connect(lambda: self._edit_camera_dialog(camera_asset))

        delete_action = menu.addAction(QIcon(":/icons/trash.svg"), self.tr("Supprimer (Archiver)"))
        delete_action.triggered.connect(lambda: self._remove_camera_logic(camera_asset))

        menu.exec_(self.camera_list_widget.mapToGlobal(pos))

    def _notify_main_window(self, title, message, msg_type='INFO'):
        # Attempt to call notify on parent if it exists (passed from DocumentManager)
        if hasattr(self.parent(), 'notify'):
            self.parent().notify(title, message, type=msg_type)
        else: # Fallback if notify is not available
            level = QMessageBox.Information
            if msg_type == 'ERROR': level = QMessageBox.Critical
            elif msg_type == 'WARNING': level = QMessageBox.Warning
            QMessageBox(level, title, message, QMessageBox.Ok, self).show()

    def set_current_user_id(self, user_id): # Called by main_window
        self.current_user_id = user_id
        logger.info(f"CameraManagementWidget: current_user_id mis à jour à {user_id}")


import pytest
from unittest.mock import MagicMock, patch
from pyshaft.web import inputs, interactions
import os

def test_select_options_callback():
    with patch("pyshaft.web.inputs.run_action") as mock_run_action:
        inputs.select_options("css=select", ["val1", 2])
        
        # Get the callback function passed to run_action
        args = mock_run_action.call_args[0]
        action_name, locator, callback = args
        
        assert action_name == "select_options"
        assert locator == "css=select"
        
        # Mock the WebElement and Select
        mock_element = MagicMock()
        with patch("pyshaft.web.inputs.Select") as mock_select_cls:
            mock_select_instance = mock_select_cls.return_value
            mock_select_instance.is_multiple = True
            
            callback(mock_element)
            
            # Verify Select was instantiated with element
            mock_select_cls.assert_called_once_with(mock_element)
            
            # Verify calls to select methods
            mock_select_instance.select_by_value.assert_called_with("val1")
            mock_select_instance.select_by_index.assert_called_with(2)

def test_deselect_option_callback():
    with patch("pyshaft.web.inputs.run_action") as mock_run_action:
        inputs.deselect_option("css=select", "val1")
        
        args = mock_run_action.call_args[0]
        callback = args[2]
        
        mock_element = MagicMock()
        with patch("pyshaft.web.inputs.Select") as mock_select_cls:
            mock_select_instance = mock_select_cls.return_value
            callback(mock_element)
            mock_select_instance.deselect_by_value.assert_called_with("val1")

def test_deselect_all_options_callback():
    with patch("pyshaft.web.inputs.run_action") as mock_run_action:
        inputs.deselect_all_options("css=select")
        
        args = mock_run_action.call_args[0]
        callback = args[2]
        
        mock_element = MagicMock()
        with patch("pyshaft.web.inputs.Select") as mock_select_cls:
            mock_select_instance = mock_select_cls.return_value
            callback(mock_element)
            mock_select_instance.deselect_all.assert_called_once()

def test_upload_files_callback():
    with patch("pyshaft.web.inputs.run_action") as mock_run_action:
        with patch("pyshaft.web.inputs.os.path.abspath", side_effect=lambda x: f"/abs/{x}"):
            inputs.upload_files("css=input", ["file1.txt", "file2.txt"])
            
            args = mock_run_action.call_args[0]
            action_name, locator, callback = args
            
            assert action_name == "upload_files"
            
            mock_element = MagicMock()
            callback(mock_element)
            
            # Selenium joins multiple files with newline
            mock_element.send_keys.assert_called_once_with("/abs/file1.txt\n/abs/file2.txt")

def test_download_file_logic():
    with patch("pyshaft.web.interactions.click") as mock_click:
        with patch("pyshaft.web.interactions.os.listdir") as mock_listdir:
            with patch("pyshaft.web.interactions.os.path.getmtime", return_value=123):
                with patch("pyshaft.web.interactions.time.sleep"):
                    # Initial state: no files
                    mock_listdir.side_effect = [
                        [], # initial snapshot
                        ["file.txt"] # after click
                    ]
                    
                    res = interactions.download_file("css=button")
                    assert res.endswith("file.txt")
                    mock_click.assert_called_once_with("css=button")

def test_get_selected_options_callback():
    from pyshaft.web import data_extract
    with patch("pyshaft.web.data_extract.run_action") as mock_run_action:
        data_extract.get_selected_options("css=select")
        
        args = mock_run_action.call_args[0]
        callback = args[2]
        
        mock_element = MagicMock()
        with patch("pyshaft.web.data_extract.Select") as mock_select_cls:
            mock_select_instance = mock_select_cls.return_value
            mock_opt1 = MagicMock()
            mock_opt1.text = "Opt 1"
            mock_opt2 = MagicMock()
            mock_opt2.text = "Opt 2"
            mock_select_instance.all_selected_options = [mock_opt1, mock_opt2]
            
            res = callback(mock_element)
            assert res == ["Opt 1", "Opt 2"]

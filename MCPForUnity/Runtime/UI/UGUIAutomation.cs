#if ENABLE_UGUI
using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace MCPForUnity.Runtime.UI
{
    /// <summary>
    /// Runtime automation for uGUI (Unity Canvas-based UI).
    /// Works with Buttons, InputFields, Sliders, Toggles, Dropdowns, ScrollViews, etc.
    /// </summary>
    public class UGUIAutomation : RuntimeUIAutomation
    {
        public override string UISystemName => "uGUI";

        #region Singleton
        public static UGUIAutomation UGUIInstance
        {
            get
            {
                if (s_instance == null)
                {
                    var go = new GameObject("UGUIAutomation");
                    s_instance = go.AddComponent<UGUIAutomation>();
                    DontDestroyOnLoad(go);
                }
                return s_instance as UGUIAutomation;
            }
        }
        #endregion

        #region Find Elements
        public override List<ElementInfo> FindElements(ElementQuery query)
        {
            var results = new List<ElementInfo>();

            if (!IsPlayMode)
            {
                LogError("UI automation only works in Play mode");
                return results;
            }

            // Get all canvases
            var canvases = FindObjectsOfType<Canvas>();
            foreach (var canvas in canvases)
            {
                if (!canvas.enabled) continue;
                SearchHierarchy(canvas.transform, query, results, "");
            }

            return results.Take(query.MaxResults).ToList();
        }

        private void SearchHierarchy(Transform parent, ElementQuery query, List<ElementInfo> results, string currentPath)
        {
            if (results.Count >= query.MaxResults) return;

            string path = string.IsNullOrEmpty(currentPath) 
                ? parent.name 
                : $"{currentPath}/{parent.name}";

            // Check if current transform matches query
            if (MatchesQuery(parent, query, path))
            {
                var info = CreateElementInfo(parent, path);
                if (query.IncludeInvisible || info.IsVisible)
                {
                    results.Add(info);
                }
            }

            // Search children
            foreach (Transform child in parent)
            {
                SearchHierarchy(child, query, results, path);
            }
        }

        private bool MatchesQuery(Transform transform, ElementQuery query, string path)
        {
            // Check path
            if (!string.IsNullOrEmpty(query.ElementPath))
            {
                if (!path.Equals(query.ElementPath, StringComparison.OrdinalIgnoreCase) &&
                    !path.EndsWith($"/{query.ElementPath}", StringComparison.OrdinalIgnoreCase))
                    return false;
            }

            // Check name
            if (!string.IsNullOrEmpty(query.ElementName))
            {
                if (!transform.name.Equals(query.ElementName, StringComparison.OrdinalIgnoreCase))
                    return false;
            }

            // Check type (component type)
            if (!string.IsNullOrEmpty(query.ElementType))
            {
                var type = GetElementType(transform);
                if (!type.Equals(query.ElementType, StringComparison.OrdinalIgnoreCase))
                    return false;
            }

            // Check text content
            if (!string.IsNullOrEmpty(query.ElementText))
            {
                string text = GetElementText(transform);
                if (string.IsNullOrEmpty(text) || !text.Contains(query.ElementText, StringComparison.OrdinalIgnoreCase))
                    return false;
            }

            // Check automation ID (uses tag for uGUI)
            if (!string.IsNullOrEmpty(query.AutomationId))
            {
                if (!transform.CompareTag(query.AutomationId))
                    return false;
            }

            return true;
        }

        private string GetElementType(Transform transform)
        {
            if (transform.GetComponent<Button>() != null) return "Button";
            if (transform.GetComponent<InputField>() != null) return "InputField";
            if (transform.GetComponent<TMPro.TMP_InputField>() != null) return "InputField";
            if (transform.GetComponent<Slider>() != null) return "Slider";
            if (transform.GetComponent<Toggle>() != null) return "Toggle";
            if (transform.GetComponent<Dropdown>() != null) return "Dropdown";
            if (transform.GetComponent<TMPro.TMP_Dropdown>() != null) return "Dropdown";
            if (transform.GetComponent<ScrollRect>() != null) return "ScrollView";
            if (transform.GetComponent<Text>() != null) return "Text";
            if (transform.GetComponent<TMPro.TextMeshProUGUI>() != null) return "Text";
            if (transform.GetComponent<Image>() != null) return "Image";
            if (transform.GetComponent<RawImage>() != null) return "RawImage";
            if (transform.GetComponent<Canvas>() != null) return "Canvas";
            if (transform.GetComponent<RectTransform>() != null) return "RectTransform";
            return "GameObject";
        }

        private string GetElementText(Transform transform)
        {
            var text = transform.GetComponent<Text>();
            if (text != null) return text.text;

            var tmpText = transform.GetComponent<TMPro.TextMeshProUGUI>();
            if (tmpText != null) return tmpText.text;

            var inputField = transform.GetComponent<InputField>();
            if (inputField != null) return inputField.text;

            var tmpInput = transform.GetComponent<TMPro.TMP_InputField>();
            if (tmpInput != null) return tmpInput.text;

            var button = transform.GetComponent<Button>();
            if (button != null)
            {
                // Try to get button text from child
                var btnText = button.GetComponentInChildren<Text>();
                if (btnText != null) return btnText.text;
                
                var btnTmpText = button.GetComponentInChildren<TMPro.TextMeshProUGUI>();
                if (btnTmpText != null) return btnTmpText.text;
            }

            return null;
        }
        #endregion

        #region Element State
        public override ElementState GetElementState(string elementPath)
        {
            var state = new ElementState { Exists = false, Path = elementPath };

            if (!IsPlayMode)
            {
                LogError("UI automation only works in Play mode");
                return state;
            }

            var transform = FindTransformByPath(elementPath);
            if (transform == null)
            {
                return state;
            }

            state.Exists = true;
            state.Name = transform.name;
            state.Type = GetElementType(transform);
            state.Text = GetElementText(transform);
            state.IsVisible = IsElementVisible(transform);
            state.IsEnabled = IsElementEnabled(transform);
            state.IsInteractable = IsElementInteractable(transform);
            state.Position = GetElementScreenPosition(transform);
            state.Size = GetElementSize(transform);
            state.Value = GetElementValue(transform);
            state.IsSelected = IsElementSelected(transform);
            state.IsFocused = IsElementFocused(transform);

            // Get children
            var children = new List<ElementInfo>();
            foreach (Transform child in transform)
            {
                string childPath = $"{elementPath}/{child.name}";
                children.Add(CreateElementInfo(child, childPath));
            }
            state.Children = children;

            return state;
        }
        #endregion

        #region Actions
        public override bool Click(string elementPath)
        {
            if (!IsPlayMode)
            {
                LogError("UI automation only works in Play mode");
                return false;
            }

            var transform = FindTransformByPath(elementPath);
            if (transform == null)
            {
                LogError($"Element not found: {elementPath}");
                return false;
            }

            // Try to find and click the button
            var button = transform.GetComponent<Button>();
            if (button != null && button.interactable)
            {
                button.onClick?.Invoke();
                OnElementClicked?.Invoke(elementPath);
                LogInfo($"Clicked button: {elementPath}");
                return true;
            }

            // Try to find and toggle a toggle
            var toggle = transform.GetComponent<Toggle>();
            if (toggle != null && toggle.interactable)
            {
                toggle.isOn = !toggle.isOn;
                OnElementClicked?.Invoke(elementPath);
                LogInfo($"Toggled: {elementPath}");
                return true;
            }

            // Use EventTrigger for generic click
            var eventTrigger = transform.GetComponent<EventTrigger>();
            if (eventTrigger != null)
            {
                var pointerClick = eventTrigger.triggers.Find(t => t.eventID == EventTriggerType.PointerClick);
                if (pointerClick != null)
                {
                    pointerClick.callback?.Invoke(null);
                    OnElementClicked?.Invoke(elementPath);
                    LogInfo($"Triggered click event: {elementPath}");
                    return true;
                }
            }

            // Simulate pointer click using ExecuteEvents
            var pointerEventData = new PointerEventData(EventSystem.current);
            ExecuteEvents.Execute(transform.gameObject, pointerEventData, ExecuteEvents.pointerClickHandler);
            OnElementClicked?.Invoke(elementPath);
            LogInfo($"Simulated click: {elementPath}");
            return true;
        }

        public override bool SetText(string elementPath, string text)
        {
            if (!IsPlayMode)
            {
                LogError("UI automation only works in Play mode");
                return false;
            }

            var transform = FindTransformByPath(elementPath);
            if (transform == null)
            {
                LogError($"Element not found: {elementPath}");
                return false;
            }

            // Try InputField
            var inputField = transform.GetComponent<InputField>();
            if (inputField != null)
            {
                inputField.text = text;
                OnTextEntered?.Invoke(elementPath, text);
                LogInfo($"Set text in InputField: {elementPath}");
                return true;
            }

            // Try TMP_InputField
            var tmpInput = transform.GetComponent<TMPro.TMP_InputField>();
            if (tmpInput != null)
            {
                tmpInput.text = text;
                OnTextEntered?.Invoke(elementPath, text);
                LogInfo($"Set text in TMP_InputField: {elementPath}");
                return true;
            }

            LogError($"Element is not an input field: {elementPath}");
            return false;
        }

        public override bool SetValue(string elementPath, object value)
        {
            if (!IsPlayMode)
            {
                LogError("UI automation only works in Play mode");
                return false;
            }

            var transform = FindTransformByPath(elementPath);
            if (transform == null)
            {
                LogError($"Element not found: {elementPath}");
                return false;
            }

            // Try Slider
            var slider = transform.GetComponent<Slider>();
            if (slider != null)
            {
                if (value is float floatValue || value is double)
                {
                    slider.value = Convert.ToSingle(value);
                    OnValueChanged?.Invoke(elementPath, slider.value);
                    LogInfo($"Set slider value: {elementPath} = {slider.value}");
                    return true;
                }
            }

            // Try Toggle
            var toggle = transform.GetComponent<Toggle>();
            if (toggle != null)
            {
                if (value is bool boolValue)
                {
                    toggle.isOn = boolValue;
                    OnValueChanged?.Invoke(elementPath, toggle.isOn);
                    LogInfo($"Set toggle value: {elementPath} = {toggle.isOn}");
                    return true;
                }
            }

            // Try Dropdown
            var dropdown = transform.GetComponent<Dropdown>();
            if (dropdown != null)
            {
                if (value is int intValue)
                {
                    dropdown.value = intValue;
                    OnValueChanged?.Invoke(elementPath, dropdown.value);
                    LogInfo($"Set dropdown value: {elementPath} = {dropdown.value}");
                    return true;
                }
            }

            // Try TMP_Dropdown
            var tmpDropdown = transform.GetComponent<TMPro.TMP_Dropdown>();
            if (tmpDropdown != null)
            {
                if (value is int tmpIntValue)
                {
                    tmpDropdown.value = tmpIntValue;
                    OnValueChanged?.Invoke(elementPath, tmpDropdown.value);
                    LogInfo($"Set TMP_Dropdown value: {elementPath} = {tmpDropdown.value}");
                    return true;
                }
            }

            LogError($"Element does not support value setting: {elementPath}");
            return false;
        }

        public override bool Scroll(string elementPath, Vector2 delta, bool scrollToEnd)
        {
            if (!IsPlayMode)
            {
                LogError("UI automation only works in Play mode");
                return false;
            }

            var transform = FindTransformByPath(elementPath);
            if (transform == null)
            {
                LogError($"Element not found: {elementPath}");
                return false;
            }

            var scrollRect = transform.GetComponent<ScrollRect>();
            if (scrollRect == null)
            {
                LogError($"Element is not a ScrollView: {elementPath}");
                return false;
            }

            if (scrollToEnd)
            {
                scrollRect.normalizedPosition = new Vector2(0, 0);
                LogInfo($"Scrolled to end: {elementPath}");
            }
            else
            {
                Vector2 newPos = scrollRect.normalizedPosition;
                newPos.x += delta.x / 1000f; // Convert to normalized
                newPos.y += delta.y / 1000f;
                newPos.x = Mathf.Clamp01(newPos.x);
                newPos.y = Mathf.Clamp01(newPos.y);
                scrollRect.normalizedPosition = newPos;
                LogInfo($"Scrolled: {elementPath} by {delta}");
            }

            return true;
        }

        public override bool Hover(string elementPath)
        {
            if (!IsPlayMode)
            {
                LogError("UI automation only works in Play mode");
                return false;
            }

            var transform = FindTransformByPath(elementPath);
            if (transform == null)
            {
                LogError($"Element not found: {elementPath}");
                return false;
            }

            // Simulate pointer enter
            var pointerEventData = new PointerEventData(EventSystem.current);
            ExecuteEvents.Execute(transform.gameObject, pointerEventData, ExecuteEvents.pointerEnterHandler);
            
            LogInfo($"Hovered over: {elementPath}");
            return true;
        }

        public override string GetScreenshot(string elementPath, int maxResolution)
        {
            if (!IsPlayMode)
            {
                LogError("UI automation only works in Play mode");
                return null;
            }

            var transform = FindTransformByPath(elementPath);
            if (transform == null)
            {
                LogError($"Element not found: {elementPath}");
                return null;
            }

            var rectTransform = transform.GetComponent<RectTransform>();
            if (rectTransform == null)
            {
                LogError($"Element is not a UI element: {elementPath}");
                return null;
            }

            // Get screen bounds
            Vector3[] corners = new Vector3[4];
            rectTransform.GetWorldCorners(corners);

            // Convert to screen coordinates
            Vector2 min = RectTransformUtility.WorldToScreenPoint(null, corners[0]);
            Vector2 max = RectTransformUtility.WorldToScreenPoint(null, corners[2]);

            int width = Mathf.RoundToInt(max.x - min.x);
            int height = Mathf.RoundToInt(max.y - min.y);

            // Clamp to screen bounds
            width = Mathf.Min(width, Screen.width - Mathf.RoundToInt(min.x));
            height = Mathf.Min(height, Screen.height - Mathf.RoundToInt(min.y));

            if (width <= 0 || height <= 0)
            {
                LogError($"Element is off-screen or has zero size: {elementPath}");
                return null;
            }

            // Capture the region
            try
            {
                Texture2D screenshot = new Texture2D(width, height, TextureFormat.RGB24, false);
                screenshot.ReadPixels(new Rect(min.x, min.y, width, height), 0, 0);
                screenshot.Apply();

                // Downscale if needed
                if (maxResolution > 0 && (width > maxResolution || height > maxResolution))
                {
                    float scale = Mathf.Min((float)maxResolution / width, (float)maxResolution / height);
                    int newWidth = Mathf.RoundToInt(width * scale);
                    int newHeight = Mathf.RoundToInt(height * scale);
                    
                    Texture2D scaled = ScaleTexture(screenshot, newWidth, newHeight);
                    Destroy(screenshot);
                    screenshot = scaled;
                }

                byte[] pngData = screenshot.EncodeToPNG();
                Destroy(screenshot);

                return Convert.ToBase64String(pngData);
            }
            catch (Exception ex)
            {
                LogError($"Failed to capture screenshot: {ex.Message}");
                return null;
            }
        }
        #endregion

        #region Helper Methods
        private Transform FindTransformByPath(string path)
        {
            if (string.IsNullOrEmpty(path))
                return null;

            // Try direct name match first
            var allTransforms = FindObjectsOfType<Transform>(true);
            foreach (var t in allTransforms)
            {
                if (GetFullPath(t).Equals(path, StringComparison.OrdinalIgnoreCase))
                    return t;
            }

            // Try finding by partial path
            string[] parts = path.Split('/');
            if (parts.Length == 0) return null;

            // Find root
            Transform root = null;
            foreach (var t in allTransforms)
            {
                if (t.parent == null && t.name.Equals(parts[0], StringComparison.OrdinalIgnoreCase))
                {
                    root = t;
                    break;
                }
            }

            if (root == null) return null;

            // Traverse path
            Transform current = root;
            for (int i = 1; i < parts.Length; i++)
            {
                Transform child = null;
                foreach (Transform c in current)
                {
                    if (c.name.Equals(parts[i], StringComparison.OrdinalIgnoreCase))
                    {
                        child = c;
                        break;
                    }
                }
                if (child == null) return null;
                current = child;
            }

            return current;
        }

        private string GetFullPath(Transform transform)
        {
            if (transform.parent == null)
                return transform.name;
            return $"{GetFullPath(transform.parent)}/{transform.name}";
        }

        private ElementInfo CreateElementInfo(Transform transform, string path)
        {
            var rectTransform = transform.GetComponent<RectTransform>();
            var info = new ElementInfo
            {
                Path = path,
                Name = transform.name,
                Type = GetElementType(transform),
                Text = GetElementText(transform),
                AutomationId = transform.tag,
                Position = GetElementScreenPosition(transform),
                Size = GetElementSize(transform),
                IsVisible = IsElementVisible(transform),
                IsInteractable = IsElementInteractable(transform),
                ChildCount = transform.childCount,
                ParentPath = transform.parent != null ? GetFullPath(transform.parent) : null,
                ChildrenPaths = new List<string>(),
                Metadata = new Dictionary<string, object>()
            };

            foreach (Transform child in transform)
            {
                info.ChildrenPaths.Add($"{path}/{child.name}");
            }

            return info;
        }

        private bool IsElementVisible(Transform transform)
        {
            var canvas = transform.GetComponentInParent<Canvas>();
            if (canvas != null && !canvas.enabled) return false;

            var graphic = transform.GetComponent<Graphic>();
            if (graphic != null)
            {
                return graphic.enabled && graphic.color.a > 0.01f;
            }

            return transform.gameObject.activeInHierarchy;
        }

        private bool IsElementEnabled(Transform transform)
        {
            var selectable = transform.GetComponent<Selectable>();
            if (selectable != null)
                return selectable.enabled;

            return transform.gameObject.activeInHierarchy;
        }

        private bool IsElementInteractable(Transform transform)
        {
            var selectable = transform.GetComponent<Selectable>();
            if (selectable != null)
                return selectable.interactable;

            return true;
        }

        private bool IsElementSelected(Transform transform)
        {
            var selectable = transform.GetComponent<Selectable>();
            if (selectable != null)
                return selectable == EventSystem.current?.currentSelectedGameObject?.GetComponent<Selectable>();

            return false;
        }

        private bool IsElementFocused(Transform transform)
        {
            return EventSystem.current?.currentSelectedGameObject == transform.gameObject;
        }

        private Vector2 GetElementScreenPosition(Transform transform)
        {
            var rectTransform = transform.GetComponent<RectTransform>();
            if (rectTransform != null)
            {
                Vector3[] corners = new Vector3[4];
                rectTransform.GetWorldCorners(corners);
                Vector2 screenPos = RectTransformUtility.WorldToScreenPoint(null, corners[0]);
                return screenPos;
            }

            return Camera.main?.WorldToScreenPoint(transform.position) ?? Vector2.zero;
        }

        private Vector2 GetElementSize(Transform transform)
        {
            var rectTransform = transform.GetComponent<RectTransform>();
            if (rectTransform != null)
            {
                Vector3[] corners = new Vector3[4];
                rectTransform.GetWorldCorners(corners);
                Vector2 min = RectTransformUtility.WorldToScreenPoint(null, corners[0]);
                Vector2 max = RectTransformUtility.WorldToScreenPoint(null, corners[2]);
                return new Vector2(max.x - min.x, max.y - min.y);
            }

            return new Vector2(100, 100); // Default size
        }

        private object GetElementValue(Transform transform)
        {
            var slider = transform.GetComponent<Slider>();
            if (slider != null) return slider.value;

            var toggle = transform.GetComponent<Toggle>();
            if (toggle != null) return toggle.isOn;

            var dropdown = transform.GetComponent<Dropdown>();
            if (dropdown != null) return dropdown.value;

            var tmpDropdown = transform.GetComponent<TMPro.TMP_Dropdown>();
            if (tmpDropdown != null) return tmpDropdown.value;

            var inputField = transform.GetComponent<InputField>();
            if (inputField != null) return inputField.text;

            var tmpInput = transform.GetComponent<TMPro.TMP_InputField>();
            if (tmpInput != null) return tmpInput.text;

            var scrollbar = transform.GetComponent<Scrollbar>();
            if (scrollbar != null) return scrollbar.value;

            return null;
        }

        private Texture2D ScaleTexture(Texture2D source, int targetWidth, int targetHeight)
        {
            RenderTexture rt = RenderTexture.GetTemporary(targetWidth, targetHeight, 0, RenderTextureFormat.ARGB32);
            rt.filterMode = FilterMode.Bilinear;
            
            RenderTexture.active = rt;
            Graphics.Blit(source, rt);
            
            Texture2D result = new Texture2D(targetWidth, targetHeight, TextureFormat.RGB24, false);
            result.ReadPixels(new Rect(0, 0, targetWidth, targetHeight), 0, 0);
            result.Apply();
            
            RenderTexture.ReleaseTemporary(rt);
            RenderTexture.active = null;
            
            return result;
        }
        #endregion
    }
}
#endif

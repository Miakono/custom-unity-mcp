#if ENABLE_UI_TOOLKIT_RUNTIME
using System;
using System.Collections.Generic;
using System.Linq;
using MCPForUnity.Runtime.Helpers;
using UnityEngine;
using UnityEngine.UIElements;

namespace MCPForUnity.Runtime.UI
{
    /// <summary>
    /// Runtime automation for UI Toolkit VisualElements.
    /// Works with Buttons, TextFields, Sliders, Toggles, Dropdowns, etc. at runtime.
    /// </summary>
    public class UIToolkitAutomation : RuntimeUIAutomation
    {
        public override string UISystemName => "UI Toolkit";

        #region Singleton
        public static UIToolkitAutomation ToolkitInstance
        {
            get
            {
                if (s_instance == null)
                {
                    var go = new GameObject("UIToolkitAutomation");
                    s_instance = go.AddComponent<UIToolkitAutomation>();
                    DontDestroyOnLoad(go);
                }
                return s_instance as UIToolkitAutomation;
            }
        }
        #endregion

        #region Properties
        private List<UIDocument> ActiveDocuments => UnityObjectCompatibility.FindObjectsByType<UIDocument>().ToList();
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

            foreach (var doc in ActiveDocuments)
            {
                if (doc.rootVisualElement == null) continue;
                
                SearchVisualTree(doc.rootVisualElement, query, results, doc.name);
            }

            return results.Take(query.MaxResults).ToList();
        }

        private void SearchVisualTree(VisualElement root, ElementQuery query, List<ElementInfo> results, string documentName)
        {
            if (results.Count >= query.MaxResults) return;

            // Search this element and all descendants
            root.Query().ForEach(element =>
            {
                if (results.Count >= query.MaxResults) return;

                string path = GetElementPath(element, documentName);
                
                if (MatchesQuery(element, query, path))
                {
                    var info = CreateElementInfo(element, path);
                    if (query.IncludeInvisible || info.IsVisible)
                    {
                        results.Add(info);
                    }
                }
            });
        }

        private bool MatchesQuery(VisualElement element, ElementQuery query, string path)
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
                if (!element.name.Equals(query.ElementName, StringComparison.OrdinalIgnoreCase))
                    return false;
            }

            // Check type
            if (!string.IsNullOrEmpty(query.ElementType))
            {
                string typeName = element.GetType().Name;
                if (!typeName.Equals(query.ElementType, StringComparison.OrdinalIgnoreCase) &&
                    !typeName.EndsWith(query.ElementType, StringComparison.OrdinalIgnoreCase))
                    return false;
            }

            // Check text content
            if (!string.IsNullOrEmpty(query.ElementText))
            {
                string text = GetElementText(element);
                if (string.IsNullOrEmpty(text) || 
                    !text.Contains(query.ElementText, StringComparison.OrdinalIgnoreCase))
                    return false;
            }

            // Check automation ID (name attribute or custom data)
            if (!string.IsNullOrEmpty(query.AutomationId))
            {
                string automationId = GetAutomationId(element);
                if (!automationId.Equals(query.AutomationId, StringComparison.OrdinalIgnoreCase))
                    return false;
            }

            return true;
        }

        private string GetElementPath(VisualElement element, string documentName)
        {
            var parts = new List<string>();
            var current = element;
            
            while (current != null)
            {
                string name = !string.IsNullOrEmpty(current.name) 
                    ? current.name 
                    : $"[{current.GetType().Name}]";
                parts.Insert(0, name);
                current = current.parent;
            }

            return $"{documentName}/{string.Join("/", parts)}";
        }

        private string GetElementType(VisualElement element)
        {
            return element.GetType().Name;
        }

        private string GetElementText(VisualElement element)
        {
            // Try different text properties based on element type
            if (element is Label label)
                return label.text;
            
            if (element is Button btn)
                return btn.text;
            
            if (element is TextField textField)
                return textField.value;
            
            if (element is TextElement textElement)
                return textElement.text;

            // Try to get text via reflection for custom elements
            var textProperty = element.GetType().GetProperty("text", 
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
            if (textProperty != null && textProperty.PropertyType == typeof(string))
            {
                return textProperty.GetValue(element) as string;
            }

            var valueProperty = element.GetType().GetProperty("value",
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
            if (valueProperty != null && valueProperty.PropertyType == typeof(string))
            {
                return valueProperty.GetValue(element) as string;
            }

            return null;
        }

        private string GetAutomationId(VisualElement element)
        {
            // Use name as primary automation ID
            if (!string.IsNullOrEmpty(element.name))
                return element.name;

            // Check for custom data attribute
            if (element is VisualElement ve && ve.userData is string data)
                return data;

            // Check viewDataKey
            if (!string.IsNullOrEmpty(element.viewDataKey))
                return element.viewDataKey;

            return string.Empty;
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

            var element = FindElementByPath(elementPath);
            if (element == null)
            {
                return state;
            }

            state.Exists = true;
            state.Name = element.name;
            state.Type = GetElementType(element);
            state.Text = GetElementText(element);
            state.IsVisible = element.visible && element.resolvedStyle.opacity > 0.01f;
            state.IsEnabled = element.enabledInHierarchy;
            state.IsInteractable = element.enabledInHierarchy && element.pickingMode == PickingMode.Position;
            state.Position = element.worldBound.position;
            state.Size = new Vector2(element.worldBound.width, element.worldBound.height);
            state.Value = GetElementValue(element);
            state.Alpha = element.resolvedStyle.opacity;
            state.IsFocused = element.focusController?.focusedElement == element;

            // Get children
            var children = new List<ElementInfo>();
            foreach (var child in element.Children())
            {
                string childPath = $"{elementPath}/{(!string.IsNullOrEmpty(child.name) ? child.name : $"[{child.GetType().Name}]")}";
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

            var element = FindElementByPath(elementPath);
            if (element == null)
            {
                LogError($"Element not found: {elementPath}");
                return false;
            }

            // Try as Button
            if (element is Button button)
            {
                button.clickable?.Invoke();
                OnElementClicked?.Invoke(elementPath);
                LogInfo($"Clicked button: {elementPath}");
                return true;
            }

            // Try as Toggle
            if (element is Toggle toggle)
            {
                toggle.value = !toggle.value;
                OnElementClicked?.Invoke(elementPath);
                LogInfo($"Toggled: {elementPath}");
                return true;
            }

            // Simulate click event
            var clickEvent = ClickEvent.GetPooled();
            clickEvent.target = element;
            element.SendEvent(clickEvent);
            
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

            var element = FindElementByPath(elementPath);
            if (element == null)
            {
                LogError($"Element not found: {elementPath}");
                return false;
            }

            // Try as TextField
            if (element is TextField textField)
            {
                textField.value = text;
                OnTextEntered?.Invoke(elementPath, text);
                LogInfo($"Set text in TextField: {elementPath}");
                return true;
            }

            // Try setting via reflection
            var valueProperty = element.GetType().GetProperty("value",
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
            if (valueProperty != null && valueProperty.PropertyType == typeof(string))
            {
                valueProperty.SetValue(element, text);
                OnTextEntered?.Invoke(elementPath, text);
                LogInfo($"Set text: {elementPath}");
                return true;
            }

            LogError($"Element is not a text input: {elementPath}");
            return false;
        }

        public override bool SetValue(string elementPath, object value)
        {
            if (!IsPlayMode)
            {
                LogError("UI automation only works in Play mode");
                return false;
            }

            var element = FindElementByPath(elementPath);
            if (element == null)
            {
                LogError($"Element not found: {elementPath}");
                return false;
            }

            // Try as Slider
            if (element is Slider slider)
            {
                if (value is float floatValue || value is double)
                {
                    slider.value = Convert.ToSingle(value);
                    OnValueChanged?.Invoke(elementPath, slider.value);
                    LogInfo($"Set slider value: {elementPath} = {slider.value}");
                    return true;
                }
            }

            // Try as SliderInt
            if (element is SliderInt sliderInt)
            {
                if (value is int intValue)
                {
                    sliderInt.value = intValue;
                    OnValueChanged?.Invoke(elementPath, sliderInt.value);
                    LogInfo($"Set slider int value: {elementPath} = {sliderInt.value}");
                    return true;
                }
            }

            // Try as Toggle
            if (element is Toggle toggle)
            {
                if (value is bool boolValue)
                {
                    toggle.value = boolValue;
                    OnValueChanged?.Invoke(elementPath, toggle.value);
                    LogInfo($"Set toggle value: {elementPath} = {toggle.value}");
                    return true;
                }
            }

            // Try as DropdownField
            if (element is DropdownField dropdown)
            {
                if (value is int indexValue)
                {
                    if (indexValue >= 0 && indexValue < dropdown.choices.Count())
                    {
                        dropdown.value = dropdown.choices.ElementAt(indexValue);
                        OnValueChanged?.Invoke(elementPath, dropdown.value);
                        LogInfo($"Set dropdown value: {elementPath} = {dropdown.value}");
                        return true;
                    }
                }
                else if (value is string stringValue)
                {
                    dropdown.value = stringValue;
                    OnValueChanged?.Invoke(elementPath, dropdown.value);
                    LogInfo($"Set dropdown value: {elementPath} = {dropdown.value}");
                    return true;
                }
            }

            // Try setting via reflection
            var valueProp = element.GetType().GetProperty("value",
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
            if (valueProp != null)
            {
                try
                {
                    var targetType = valueProp.PropertyType;
                    var convertedValue = Convert.ChangeType(value, targetType);
                    valueProp.SetValue(element, convertedValue);
                    OnValueChanged?.Invoke(elementPath, convertedValue);
                    LogInfo($"Set value: {elementPath} = {convertedValue}");
                    return true;
                }
                catch (Exception ex)
                {
                    LogError($"Failed to convert value: {ex.Message}");
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

            var element = FindElementByPath(elementPath);
            if (element == null)
            {
                LogError($"Element not found: {elementPath}");
                return false;
            }

            // Try as ScrollView
            if (element is ScrollView scrollView)
            {
                if (scrollToEnd)
                {
                    scrollView.scrollOffset = new Vector2(0, scrollView.contentContainer.layout.height);
                    LogInfo($"Scrolled to end: {elementPath}");
                }
                else
                {
                    var currentOffset = scrollView.scrollOffset;
                    scrollView.scrollOffset = new Vector2(
                        currentOffset.x + delta.x,
                        currentOffset.y + delta.y
                    );
                    LogInfo($"Scrolled: {elementPath} by {delta}");
                }
                return true;
            }

            // Try to find ScrollView as parent
            var scrollViewParent = element.GetFirstAncestorOfType<ScrollView>();
            if (scrollViewParent != null)
            {
                if (scrollToEnd)
                {
                    scrollViewParent.scrollOffset = new Vector2(0, scrollViewParent.contentContainer.layout.height);
                }
                else
                {
                    var currentOffset = scrollViewParent.scrollOffset;
                    scrollViewParent.scrollOffset = new Vector2(
                        currentOffset.x + delta.x,
                        currentOffset.y + delta.y
                    );
                }
                LogInfo($"Scrolled parent ScrollView: {elementPath}");
                return true;
            }

            LogError($"Element is not a scrollable container: {elementPath}");
            return false;
        }

        public override bool Hover(string elementPath)
        {
            if (!IsPlayMode)
            {
                LogError("UI automation only works in Play mode");
                return false;
            }

            var element = FindElementByPath(elementPath);
            if (element == null)
            {
                LogError($"Element not found: {elementPath}");
                return false;
            }

            // Simulate pointer enter
            var pointerEnterEvent = PointerEnterEvent.GetPooled();
            pointerEnterEvent.target = element;
            element.SendEvent(pointerEnterEvent);

            // Simulate mouse over
            var mouseOverEvent = MouseOverEvent.GetPooled();
            mouseOverEvent.target = element;
            element.SendEvent(mouseOverEvent);

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

            var element = FindElementByPath(elementPath);
            if (element == null)
            {
                LogError($"Element not found: {elementPath}");
                return null;
            }

            var worldBounds = element.worldBound;
            if (worldBounds.width <= 0 || worldBounds.height <= 0)
            {
                LogError($"Element has zero size or is not visible: {elementPath}");
                return null;
            }

            try
            {
                // For UI Toolkit, we need to render the panel to a texture
                var panel = element.panel;
                if (panel == null)
                {
                    LogError($"Element is not attached to a panel: {elementPath}");
                    return null;
                }

                int width = Mathf.RoundToInt(worldBounds.width);
                int height = Mathf.RoundToInt(worldBounds.height);

                // Create render texture for the full panel
                var rt = RenderTexture.GetTemporary(
                    Mathf.RoundToInt(panel.visualTree.layout.width),
                    Mathf.RoundToInt(panel.visualTree.layout.height),
                    24,
                    RenderTextureFormat.ARGB32
                );

                // Render the panel
                panel.Render(rt);

                // Read the specific element region
                RenderTexture.active = rt;
                Texture2D screenshot = new Texture2D(width, height, TextureFormat.RGB24, false);
                screenshot.ReadPixels(new Rect(worldBounds.x, rt.height - worldBounds.y - height, width, height), 0, 0);
                screenshot.Apply();
                RenderTexture.active = null;
                RenderTexture.ReleaseTemporary(rt);

                // Downscale if needed
                if (maxResolution > 0 && (width > maxResolution || height > maxResolution))
                {
                    float scale = Mathf.Min((float)maxResolution / width, (float)maxResolution / height);
                    int newWidth = Mathf.RoundToInt(width * scale);
                    int newHeight = Mathf.RoundToInt(height * scale);
                    
                    Texture2D scaled = ScaleTexture(screenshot, newWidth, newHeight);
                    Destroy(screenshot);
                    screenshot = scaled;
                    width = newWidth;
                    height = newHeight;
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
        private VisualElement FindElementByPath(string path)
        {
            if (string.IsNullOrEmpty(path))
                return null;

            string[] parts = path.Split('/');
            if (parts.Length < 2) return null;

            string documentName = parts[0];
            
            // Find the UIDocument
            var doc = ActiveDocuments.FirstOrDefault(d => d.name == documentName);
            if (doc?.rootVisualElement == null)
                return null;

            // Traverse the path
            VisualElement current = doc.rootVisualElement;
            for (int i = 1; i < parts.Length; i++)
            {
                string part = parts[i];
                
                // Handle array notation [Type]
                if (part.StartsWith("[") && part.EndsWith("]"))
                    continue;

                VisualElement found = null;
                foreach (var child in current.Children())
                {
                    if (child.name == part)
                    {
                        found = child;
                        break;
                    }
                }

                if (found == null)
                    return null;

                current = found;
            }

            return current;
        }

        private ElementInfo CreateElementInfo(VisualElement element, string path)
        {
            var info = new ElementInfo
            {
                Path = path,
                Name = element.name,
                Type = GetElementType(element),
                Text = GetElementText(element),
                AutomationId = GetAutomationId(element),
                Position = element.worldBound.position,
                Size = new Vector2(element.worldBound.width, element.worldBound.height),
                IsVisible = element.visible && element.resolvedStyle.opacity > 0.01f,
                IsInteractable = element.enabledInHierarchy && element.pickingMode == PickingMode.Position,
                ChildCount = element.childCount,
                ParentPath = element.parent != null ? GetElementPath(element.parent, path.Split('/')[0]) : null,
                ChildrenPaths = new List<string>(),
                Metadata = new Dictionary<string, object>()
            };

            foreach (var child in element.Children())
            {
                string childName = !string.IsNullOrEmpty(child.name) ? child.name : $"[{child.GetType().Name}]";
                info.ChildrenPaths.Add($"{path}/{childName}");
            }

            return info;
        }

        private object GetElementValue(VisualElement element)
        {
            if (element is Slider slider)
                return slider.value;
            
            if (element is SliderInt sliderInt)
                return sliderInt.value;
            
            if (element is Toggle toggle)
                return toggle.value;
            
            if (element is TextField textField)
                return textField.value;
            
            if (element is DropdownField dropdown)
                return dropdown.value;

            // Try reflection
            var valueProp = element.GetType().GetProperty("value",
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
            if (valueProp != null)
            {
                try
                {
                    return valueProp.GetValue(element);
                }
                catch { }
            }

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

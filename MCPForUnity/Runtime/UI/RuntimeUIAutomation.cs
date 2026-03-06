using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Events;

namespace MCPForUnity.Runtime.UI
{
    /// <summary>
    /// Base class for runtime UI automation.
    /// Provides common functionality for uGUI and UI Toolkit automation systems.
    /// This is a runtime-only tool that only works during Play mode.
    /// </summary>
    public abstract class RuntimeUIAutomation : MonoBehaviour
    {
        #region Singleton Pattern
        protected static RuntimeUIAutomation s_instance;
        public static RuntimeUIAutomation Instance
        {
            get
            {
                if (s_instance == null)
                {
                    // Try to find existing instance
                    s_instance = FindFirstObjectByType<RuntimeUIAutomation>();
                    
                    // Create new if not found
                    if (s_instance == null)
                    {
                        var go = new GameObject("RuntimeUIAutomation");
                        #if ENABLE_UGUI
                        s_instance = go.AddComponent<UGUIAutomation>();
                        #else
                        s_instance = go.AddComponent<RuntimeUIAutomation>();
                        #endif
                        DontDestroyOnLoad(go);
                    }
                }
                return s_instance;
            }
        }
        #endregion

        #region Events
        public UnityEvent<string> OnElementClicked;
        public UnityEvent<string, string> OnTextEntered;
        public UnityEvent<string, object> OnValueChanged;
        public UnityEvent<string> OnElementFound;
        public UnityEvent<string> OnAutomationError;
        #endregion

        #region Properties
        public abstract string UISystemName { get; }
        public bool IsPlayMode => Application.isPlaying;
        #endregion

        protected virtual void Awake()
        {
            if (s_instance != null && s_instance != this)
            {
                Destroy(gameObject);
                return;
            }
            s_instance = this;
            DontDestroyOnLoad(gameObject);
        }

        protected virtual void OnDestroy()
        {
            if (s_instance == this)
            {
                s_instance = null;
            }
        }

        #region Abstract Methods - Must be implemented by derived classes
        /// <summary>
        /// Find UI elements matching the specified criteria.
        /// </summary>
        public abstract List<ElementInfo> FindElements(ElementQuery query);

        /// <summary>
        /// Get detailed state of a specific element.
        /// </summary>
        public abstract ElementState GetElementState(string elementPath);

        /// <summary>
        /// Simulate a click on an element.
        /// </summary>
        public abstract bool Click(string elementPath);

        /// <summary>
        /// Set text in an input field.
        /// </summary>
        public abstract bool SetText(string elementPath, string text);

        /// <summary>
        /// Set value (slider, toggle, dropdown).
        /// </summary>
        public abstract bool SetValue(string elementPath, object value);

        /// <summary>
        /// Scroll a scroll view.
        /// </summary>
        public abstract bool Scroll(string elementPath, Vector2 delta, bool scrollToEnd);

        /// <summary>
        /// Hover over an element.
        /// </summary>
        public abstract bool Hover(string elementPath);

        /// <summary>
        /// Take a screenshot of a specific element.
        /// </summary>
        public abstract string GetScreenshot(string elementPath, int maxResolution);
        #endregion

        #region Common Methods
        /// <summary>
        /// Wait for an element to appear (coroutine-based, for use from non-async code).
        /// </summary>
        public Coroutine WaitForElementCoroutine(ElementQuery query, float timeout, Action<ElementInfo> onFound, Action onTimeout)
        {
            return StartCoroutine(WaitForElementRoutine(query, timeout, onFound, onTimeout));
        }

        private IEnumerator WaitForElementRoutine(ElementQuery query, float timeout, Action<ElementInfo> onFound, Action onTimeout)
        {
            float startTime = Time.time;
            while (Time.time - startTime < timeout)
            {
                var elements = FindElements(query);
                if (elements.Count > 0)
                {
                    onFound?.Invoke(elements[0]);
                    yield break;
                }
                yield return new WaitForSeconds(0.1f);
            }
            onTimeout?.Invoke();
        }

        /// <summary>
        /// Poll for element existence (synchronous check).
        /// </summary>
        public bool ElementExists(string elementPath)
        {
            return GetElementState(elementPath).Exists;
        }

        protected void LogError(string message)
        {
            Debug.LogError($"[{UISystemName}] {message}");
            OnAutomationError?.Invoke(message);
        }

        protected void LogWarning(string message)
        {
            Debug.LogWarning($"[{UISystemName}] {message}");
        }

        protected void LogInfo(string message)
        {
            Debug.Log($"[{UISystemName}] {message}");
        }
        #endregion
    }

    #region Data Structures
    /// <summary>
    /// Query parameters for finding UI elements.
    /// </summary>
    [Serializable]
    public class ElementQuery
    {
        public string ElementPath;
        public string ElementName;
        public string ElementType;
        public string ElementText;
        public string AutomationId;
        public int MaxResults = 50;
        public bool IncludeInvisible = false;

        public bool HasCriteria => !string.IsNullOrEmpty(ElementPath) 
            || !string.IsNullOrEmpty(ElementName) 
            || !string.IsNullOrEmpty(ElementType)
            || !string.IsNullOrEmpty(ElementText)
            || !string.IsNullOrEmpty(AutomationId);
    }

    /// <summary>
    /// Information about a found UI element.
    /// </summary>
    [Serializable]
    public class ElementInfo
    {
        public string Path;
        public string Name;
        public string Type;
        public string Text;
        public string AutomationId;
        public Vector2 Position;
        public Vector2 Size;
        public bool IsVisible;
        public bool IsInteractable;
        public int ChildCount;
        public string ParentPath;
        public List<string> ChildrenPaths;
        public Dictionary<string, object> Metadata;
    }

    /// <summary>
    /// Current state of a UI element.
    /// </summary>
    [Serializable]
    public class ElementState
    {
        public bool Exists;
        public string Path;
        public string Name;
        public string Type;
        public string Text;
        public bool IsVisible;
        public bool IsEnabled;
        public bool IsInteractable;
        public Vector2 Position;
        public Vector2 Size;
        public float Alpha;
        public object Value;
        public string PlaceholderText;
        public bool IsSelected;
        public bool IsFocused;
        public List<ElementInfo> Children;
    }
    #endregion
}

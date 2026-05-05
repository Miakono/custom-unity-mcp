using System;
using System.Collections.Generic;
using UnityEngine.UIElements;

namespace MCPForUnity.UIElements
{
    /// <summary>
    /// A modal dialog VisualElement: scrim backdrop, centered content frame,
    /// title, close button, and a body slot. The internal tree mirrors
    /// Modal.uxml. Use Open()/Close() to drive visibility; styling comes from
    /// Modal.uss + tokens.uss loaded in the same panel.
    /// </summary>
    public class Modal : VisualElement
    {
        public new class UxmlFactory : UxmlFactory<Modal, UxmlTraits> { }

        public new class UxmlTraits : VisualElement.UxmlTraits
        {
            private readonly UxmlStringAttributeDescription _title = new UxmlStringAttributeDescription
            {
                name = "title",
                defaultValue = string.Empty,
            };

            private readonly UxmlBoolAttributeDescription _showCloseButton = new UxmlBoolAttributeDescription
            {
                name = "show-close-button",
                defaultValue = true,
            };

            private readonly UxmlBoolAttributeDescription _openOnAttach = new UxmlBoolAttributeDescription
            {
                name = "open-on-attach",
                defaultValue = false,
            };

            public override IEnumerable<UxmlChildElementDescription> uxmlChildElementsDescription
            {
                get { yield return new UxmlChildElementDescription(typeof(VisualElement)); }
            }

            public override void Init(VisualElement ve, IUxmlAttributes bag, CreationContext cc)
            {
                base.Init(ve, bag, cc);
                var modal = (Modal)ve;
                modal.SetTitle(_title.GetValueFromBag(bag, cc));
                modal.SetShowCloseButton(_showCloseButton.GetValueFromBag(bag, cc));
                modal._openOnAttach = _openOnAttach.GetValueFromBag(bag, cc);
            }
        }

        public const string OpenClassName = "modal--open";

        private readonly VisualElement _scrim;
        private readonly VisualElement _content;
        private readonly Label _titleLabel;
        private readonly Button _closeButton;
        private readonly VisualElement _body;
        private Focusable _previouslyFocused;
        private bool _openOnAttach;

        public bool IsOpen => ClassListContains(OpenClassName);
        public event Action OnClosed;
        public event Action OnOpened;

        // Override contentContainer so UXML children inside <mcp:Modal>...</mcp:Modal>
        // and external SetBody-style Add() calls flow into the body slot.
        public override VisualElement contentContainer => _body ?? this;

        public Modal()
        {
            AddToClassList("modal");
            focusable = false;
            pickingMode = PickingMode.Ignore;

            _scrim = new VisualElement { name = "modal__scrim" };
            _scrim.AddToClassList("modal__scrim");
            _scrim.pickingMode = PickingMode.Position;
            hierarchy.Add(_scrim);

            _content = new VisualElement { name = "modal__content" };
            _content.AddToClassList("modal__content");
            _content.focusable = true;
            _content.pickingMode = PickingMode.Position;
            _scrim.hierarchy.Add(_content);

            var header = new VisualElement { name = "modal__header" };
            header.AddToClassList("modal__header");
            _content.hierarchy.Add(header);

            _titleLabel = new Label { name = "modal__title" };
            _titleLabel.AddToClassList("modal__title");
            header.hierarchy.Add(_titleLabel);

            _closeButton = new Button { name = "modal__close", text = "×" };
            _closeButton.AddToClassList("modal__close");
            _closeButton.clicked += Close;
            header.hierarchy.Add(_closeButton);

            _body = new VisualElement { name = "modal__body" };
            _body.AddToClassList("modal__body");
            _content.hierarchy.Add(_body);

            // Click-outside-to-close: a click on the scrim (but not bubbled from
            // content) closes the modal.
            _scrim.RegisterCallback<ClickEvent>(evt =>
            {
                if (evt.target == _scrim)
                {
                    Close();
                }
            });

            RegisterCallback<KeyDownEvent>(OnKeyDown, TrickleDown.TrickleDown);
            RegisterCallback<AttachToPanelEvent>(_ =>
            {
                if (_openOnAttach && !IsOpen)
                {
                    Open();
                }
            });
        }

        public void Open()
        {
            if (IsOpen) return;

            _previouslyFocused = focusController?.focusedElement;
            AddToClassList(OpenClassName);

            // Defer focus to next frame so the panel's layout / display state is settled.
            schedule.Execute(() =>
            {
                if (panel == null) return;
                _content.Focus();
            }).StartingIn(0);

            OnOpened?.Invoke();
        }

        public void Close()
        {
            if (!IsOpen) return;

            RemoveFromClassList(OpenClassName);

            if (_previouslyFocused is VisualElement ve && ve.panel != null)
            {
                ve.Focus();
            }
            _previouslyFocused = null;

            OnClosed?.Invoke();
        }

        public void SetTitle(string title)
        {
            _titleLabel.text = title ?? string.Empty;
        }

        public string GetTitle() => _titleLabel.text;

        public void SetBody(VisualElement bodyContent)
        {
            _body.Clear();
            if (bodyContent != null)
            {
                _body.Add(bodyContent);
            }
        }

        public void SetBodyText(string text)
        {
            _body.Clear();
            if (!string.IsNullOrEmpty(text))
            {
                _body.Add(new Label(text));
            }
        }

        public void SetShowCloseButton(bool show)
        {
            _closeButton.EnableInClassList("modal__close--hidden", !show);
        }

        public VisualElement BodySlot => _body;
        public VisualElement ContentRoot => _content;

        private void OnKeyDown(KeyDownEvent evt)
        {
            if (!IsOpen) return;

            if (evt.keyCode == UnityEngine.KeyCode.Escape)
            {
                Close();
                evt.StopPropagation();
                return;
            }

            // Focus trap: cycle Tab / Shift+Tab focus inside _content.
            if (evt.keyCode == UnityEngine.KeyCode.Tab)
            {
                var focusables = CollectFocusables(_content);
                if (focusables.Count == 0) return;

                int currentIndex = focusController != null
                    ? focusables.IndexOf(focusController.focusedElement as VisualElement)
                    : -1;

                int nextIndex;
                if (evt.shiftKey)
                {
                    nextIndex = currentIndex <= 0 ? focusables.Count - 1 : currentIndex - 1;
                }
                else
                {
                    nextIndex = currentIndex < 0 || currentIndex >= focusables.Count - 1 ? 0 : currentIndex + 1;
                }

                focusables[nextIndex].Focus();
                evt.StopPropagation();
            }
        }

        private static List<VisualElement> CollectFocusables(VisualElement root)
        {
            var list = new List<VisualElement>();
            CollectFocusablesRecursive(root, list);
            return list;
        }

        private static void CollectFocusablesRecursive(VisualElement element, List<VisualElement> sink)
        {
            for (int i = 0; i < element.childCount; i++)
            {
                var child = element[i];
                if (child.focusable && child.enabledInHierarchy && child.resolvedStyle.display != DisplayStyle.None)
                {
                    sink.Add(child);
                }
                CollectFocusablesRecursive(child, sink);
            }
        }
    }
}

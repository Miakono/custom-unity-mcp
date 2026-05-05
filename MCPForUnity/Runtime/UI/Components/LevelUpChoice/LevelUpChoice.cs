using System;
using System.Collections.Generic;
using UnityEngine.UIElements;

namespace MCPForUnity.UIElements
{
    public enum ChoiceRarity
    {
        Common,
        Uncommon,
        Rare,
        Epic,
        Legendary,
    }

    /// <summary>
    /// Data describing one selectable upgrade card. IconAssetPath is a Unity
    /// asset path (e.g. "Assets/UI/Icons/foo.png") — caller is responsible for
    /// resolving it to a Texture2D at runtime if needed; the LevelUpChoice
    /// element itself only stores the path and applies a class hook.
    /// </summary>
    [Serializable]
    public struct ChoiceData
    {
        public string Name;
        public string Description;
        public string IconAssetPath;
        public ChoiceRarity Rarity;
        public bool IsPrimary;
    }

    /// <summary>
    /// LevelUpChoice — title + horizontal row of 2-4 choice cards. Wires either
    /// runtime SetChoices() data or author-time inline cards in UXML to a
    /// shared OnChoicePicked event.
    /// </summary>
    public class LevelUpChoice : VisualElement
    {
        public new class UxmlFactory : UxmlFactory<LevelUpChoice, UxmlTraits> { }

        public new class UxmlTraits : VisualElement.UxmlTraits
        {
            private readonly UxmlStringAttributeDescription _title = new UxmlStringAttributeDescription
            {
                name = "title",
                defaultValue = "Level Up!",
            };

            public override IEnumerable<UxmlChildElementDescription> uxmlChildElementsDescription
            {
                get { yield return new UxmlChildElementDescription(typeof(VisualElement)); }
            }

            public override void Init(VisualElement ve, IUxmlAttributes bag, CreationContext cc)
            {
                base.Init(ve, bag, cc);
                var luc = (LevelUpChoice)ve;
                luc.SetTitle(_title.GetValueFromBag(bag, cc));
            }
        }

        public const string CardClass = "luc-card";
        public const string CardPrimaryClass = "luc-card--primary";
        public const string CardNameClass = "luc-card__name";
        public const string CardDescClass = "luc-card__description";
        public const string CardIconClass = "luc-card__icon";
        public const string CardPickClass = "luc-card__pick";

        private readonly Label _titleLabel;
        private readonly VisualElement _cardsContainer;
        private readonly List<VisualElement> _cards = new List<VisualElement>();

        public event Action<int> OnChoicePicked;
        public IReadOnlyList<VisualElement> Cards => _cards;

        // Override contentContainer so UXML children inside <mcp:LevelUpChoice>...</...>
        // (and external Add() calls) flow into the cards row instead of stacking
        // beside the title.
        public override VisualElement contentContainer => _cardsContainer ?? this;

        public LevelUpChoice()
        {
            AddToClassList("luc");

            _titleLabel = new Label("Level Up!") { name = "luc__title" };
            _titleLabel.AddToClassList("luc__title");
            hierarchy.Add(_titleLabel);

            _cardsContainer = new VisualElement { name = "luc__cards" };
            _cardsContainer.AddToClassList("luc__cards");
            hierarchy.Add(_cardsContainer);

            // After UXML inflation, scan for author-time cards already inside
            // _cardsContainer (or anywhere below this element) and wire them.
            RegisterCallback<AttachToPanelEvent>(_ => RebuildIndexFromExistingCards());
            RegisterCallback<GeometryChangedEvent>(OnFirstGeometry);
        }

        private void OnFirstGeometry(GeometryChangedEvent _)
        {
            UnregisterCallback<GeometryChangedEvent>(OnFirstGeometry);
            RebuildIndexFromExistingCards();
        }

        public void SetTitle(string title)
        {
            _titleLabel.text = title ?? string.Empty;
        }

        public void SetChoices(IList<ChoiceData> choices)
        {
            _cardsContainer.Clear();
            _cards.Clear();
            if (choices == null) return;

            for (int i = 0; i < choices.Count; i++)
            {
                var card = BuildCard(choices[i], i);
                _cardsContainer.Add(card);
                _cards.Add(card);
            }
        }

        private VisualElement BuildCard(ChoiceData data, int index)
        {
            var card = new VisualElement { name = $"luc-card-{index}" };
            card.AddToClassList(CardClass);
            card.AddToClassList(GetRarityClass(data.Rarity));
            if (data.IsPrimary)
            {
                card.AddToClassList(CardPrimaryClass);
            }
            card.focusable = true;

            var icon = new VisualElement { name = $"luc-card-{index}__icon" };
            icon.AddToClassList(CardIconClass);
            if (!string.IsNullOrEmpty(data.IconAssetPath))
            {
                icon.AddToClassList("luc-card__icon--has-source");
                icon.userData = data.IconAssetPath;
            }
            card.Add(icon);

            var name = new Label(data.Name ?? string.Empty) { name = $"luc-card-{index}__name" };
            name.AddToClassList(CardNameClass);
            card.Add(name);

            var desc = new Label(data.Description ?? string.Empty) { name = $"luc-card-{index}__description" };
            desc.AddToClassList(CardDescClass);
            card.Add(desc);

            var pick = new Button(() => RaiseChoicePicked(index)) { text = "Pick", name = $"luc-card-{index}__pick" };
            pick.AddToClassList(CardPickClass);
            card.Add(pick);

            return card;
        }

        private void RebuildIndexFromExistingCards()
        {
            // If SetChoices already populated, _cards is the source of truth.
            if (_cards.Count > 0) return;

            int index = 0;
            foreach (var existing in this.Query<VisualElement>(className: CardClass).ToList())
            {
                int captured = index++;
                _cards.Add(existing);
                existing.focusable = true;

                var pickButton = existing.Q<Button>(className: CardPickClass);
                if (pickButton != null)
                {
                    pickButton.clicked += () => RaiseChoicePicked(captured);
                }
            }
        }

        private void RaiseChoicePicked(int index)
        {
            OnChoicePicked?.Invoke(index);
        }

        public static string GetRarityClass(ChoiceRarity rarity)
        {
            switch (rarity)
            {
                case ChoiceRarity.Uncommon: return "luc-card--rarity-uncommon";
                case ChoiceRarity.Rare: return "luc-card--rarity-rare";
                case ChoiceRarity.Epic: return "luc-card--rarity-epic";
                case ChoiceRarity.Legendary: return "luc-card--rarity-legendary";
                case ChoiceRarity.Common:
                default:
                    return "luc-card--rarity-common";
            }
        }
    }
}

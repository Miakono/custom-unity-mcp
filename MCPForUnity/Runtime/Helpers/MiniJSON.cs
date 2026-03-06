// -----------------------------------------------------------------------
// MiniJSON.cs
// Simple JSON serialization for Unity (Runtime-compatible)
// 
// Based on the popular MiniJSON implementation.
// This is a lightweight JSON parser/serializer that works in Unity Runtime
// without external dependencies.
// -----------------------------------------------------------------------

#nullable enable

using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;

namespace MCPForUnity.Runtime
{
    /// <summary>
    /// Simple JSON parser and serializer for Unity.
    /// Works in both Editor and Runtime contexts.
    /// </summary>
    public static class MiniJSON
    {
        /// <summary>
        /// Parses a JSON string into a dictionary or list
        /// </summary>
        public static object? Deserialize(string json)
        {
            if (string.IsNullOrEmpty(json))
                return null;

            return Parser.Parse(json);
        }

        /// <summary>
        /// Serializes an object to a JSON string
        /// </summary>
        public static string Serialize(object? obj)
        {
            return Serializer.Serialize(obj);
        }

        #region Parser

        private sealed class Parser : IDisposable
        {
            private readonly string json;
            private int index;

            private Parser(string jsonString)
            {
                json = jsonString;
                index = 0;
            }

            public static object? Parse(string jsonString)
            {
                using var parser = new Parser(jsonString);
                return parser.ParseValue();
            }

            private object? ParseValue()
            {
                SkipWhitespace();
                
                if (index >= json.Length)
                    return null;

                char c = json[index];
                
                return c switch
                {
                    '"' => ParseString(),
                    '{' => ParseObject(),
                    '[' => ParseArray(),
                    't' or 'f' => ParseBool(),
                    'n' => ParseNull(),
                    '-' or >= '0' and <= '9' => ParseNumber(),
                    _ => throw new Exception($"Unexpected character: {c} at position {index}")
                };
            }

            private Dictionary<string, object> ParseObject()
            {
                var dict = new Dictionary<string, object>();
                index++; // Skip '{'
                
                SkipWhitespace();
                
                if (index < json.Length && json[index] == '}')
                {
                    index++;
                    return dict;
                }

                while (index < json.Length)
                {
                    SkipWhitespace();
                    
                    string key = ParseString();
                    
                    SkipWhitespace();
                    
                    if (index >= json.Length || json[index] != ':')
                        throw new Exception($"Expected ':' at position {index}");
                    
                    index++;
                    
                    object? value = ParseValue();
                    dict[key] = value!;
                    
                    SkipWhitespace();
                    
                    if (index >= json.Length)
                        throw new Exception("Unexpected end of JSON");
                    
                    if (json[index] == '}')
                    {
                        index++;
                        return dict;
                    }
                    
                    if (json[index] != ',')
                        throw new Exception($"Expected ',' or '}}' at position {index}");
                    
                    index++;
                }
                
                throw new Exception("Unexpected end of JSON");
            }

            private List<object> ParseArray()
            {
                var list = new List<object>();
                index++; // Skip '['
                
                SkipWhitespace();
                
                if (index < json.Length && json[index] == ']')
                {
                    index++;
                    return list;
                }

                while (index < json.Length)
                {
                    object? value = ParseValue();
                    list.Add(value!);
                    
                    SkipWhitespace();
                    
                    if (index >= json.Length)
                        throw new Exception("Unexpected end of JSON");
                    
                    if (json[index] == ']')
                    {
                        index++;
                        return list;
                    }
                    
                    if (json[index] != ',')
                        throw new Exception($"Expected ',' or ']' at position {index}");
                    
                    index++;
                }
                
                throw new Exception("Unexpected end of JSON");
            }

            private string ParseString()
            {
                index++; // Skip opening quote
                var sb = new StringBuilder();
                
                while (index < json.Length)
                {
                    char c = json[index];
                    
                    if (c == '"')
                    {
                        index++;
                        return sb.ToString();
                    }
                    
                    if (c == '\\')
                    {
                        index++;
                        if (index >= json.Length)
                            throw new Exception("Unexpected end of JSON in string");
                        
                        c = json[index] switch
                        {
                            '"' => '"',
                            '\\' => '\\',
                            '/' => '/',
                            'b' => '\b',
                            'f' => '\f',
                            'n' => '\n',
                            'r' => '\r',
                            't' => '\t',
                            'u' => ParseUnicodeEscape(),
                            _ => json[index]
                        };
                    }
                    
                    sb.Append(c);
                    index++;
                }
                
                throw new Exception("Unexpected end of JSON in string");
            }

            private char ParseUnicodeEscape()
            {
                if (index + 4 >= json.Length)
                    throw new Exception("Invalid Unicode escape sequence");
                
                string hex = json.Substring(index + 1, 4);
                index += 4;
                return (char)Convert.ToInt32(hex, 16);
            }

            private bool ParseBool()
            {
                if (json.Substring(index).StartsWith("true"))
                {
                    index += 4;
                    return true;
                }
                
                if (json.Substring(index).StartsWith("false"))
                {
                    index += 5;
                    return false;
                }
                
                throw new Exception($"Expected 'true' or 'false' at position {index}");
            }

            private object? ParseNull()
            {
                if (json.Substring(index).StartsWith("null"))
                {
                    index += 4;
                    return null;
                }
                
                throw new Exception($"Expected 'null' at position {index}");
            }

            private object ParseNumber()
            {
                int start = index;
                
                if (json[index] == '-')
                    index++;
                
                while (index < json.Length && char.IsDigit(json[index]))
                    index++;
                
                if (index < json.Length && json[index] == '.')
                {
                    index++;
                    while (index < json.Length && char.IsDigit(json[index]))
                        index++;
                }
                
                if (index < json.Length && (json[index] == 'e' || json[index] == 'E'))
                {
                    index++;
                    if (index < json.Length && (json[index] == '+' || json[index] == '-'))
                        index++;
                    while (index < json.Length && char.IsDigit(json[index]))
                        index++;
                }
                
                string numStr = json.Substring(start, index - start);
                
                if (numStr.Contains('.') || numStr.Contains('e') || numStr.Contains('E'))
                {
                    if (double.TryParse(numStr, out double d))
                        return d;
                }
                
                if (long.TryParse(numStr, out long l))
                    return l;
                
                return numStr;
            }

            private void SkipWhitespace()
            {
                while (index < json.Length && char.IsWhiteSpace(json[index]))
                    index++;
            }

            public void Dispose()
            {
                // Nothing to dispose
            }
        }

        #endregion

        #region Serializer

        private sealed class Serializer
        {
            private readonly StringBuilder sb = new();

            public static string Serialize(object? obj)
            {
                var serializer = new Serializer();
                serializer.SerializeValue(obj);
                return serializer.sb.ToString();
            }

            private void SerializeValue(object? value)
            {
                switch (value)
                {
                    case null:
                        sb.Append("null");
                        break;
                    case string s:
                        SerializeString(s);
                        break;
                    case bool b:
                        sb.Append(b ? "true" : "false");
                        break;
                    case Dictionary<string, object> dict:
                        SerializeObject(dict);
                        break;
                    case IList list:
                        SerializeArray(list);
                        break;
                    case float f:
                        sb.Append(f.ToString("R"));
                        break;
                    case double d:
                        sb.Append(d.ToString("R"));
                        break;
                    case int i:
                        sb.Append(i);
                        break;
                    case long l:
                        sb.Append(l);
                        break;
                    default:
                        SerializeString(value.ToString()!);
                        break;
                }
            }

            private void SerializeObject(Dictionary<string, object> dict)
            {
                sb.Append('{');
                bool first = true;
                
                foreach (var kvp in dict)
                {
                    if (!first)
                        sb.Append(',');
                    
                    SerializeString(kvp.Key);
                    sb.Append(':');
                    SerializeValue(kvp.Value);
                    
                    first = false;
                }
                
                sb.Append('}');
            }

            private void SerializeArray(IList list)
            {
                sb.Append('[');
                bool first = true;
                
                foreach (var item in list)
                {
                    if (!first)
                        sb.Append(',');
                    
                    SerializeValue(item);
                    
                    first = false;
                }
                
                sb.Append(']');
            }

            private void SerializeString(string str)
            {
                sb.Append('"');
                
                foreach (char c in str)
                {
                    switch (c)
                    {
                        case '"':
                            sb.Append("\\\"");
                            break;
                        case '\\':
                            sb.Append("\\\\");
                            break;
                        case '\b':
                            sb.Append("\\b");
                            break;
                        case '\f':
                            sb.Append("\\f");
                            break;
                        case '\n':
                            sb.Append("\\n");
                            break;
                        case '\r':
                            sb.Append("\\r");
                            break;
                        case '\t':
                            sb.Append("\\t");
                            break;
                        default:
                            if (c < 0x20)
                                sb.Append($"\\u{(int)c:X4}");
                            else
                                sb.Append(c);
                            break;
                    }
                }
                
                sb.Append('"');
            }
        }

        #endregion

        #region Extension Methods

        /// <summary>
        /// Gets a value from a dictionary with a default fallback
        /// </summary>
        public static TValue GetValueOrDefault<TKey, TValue>(
            this Dictionary<TKey, TValue> dict,
            TKey key,
            TValue defaultValue = default!
        ) where TKey : notnull
        {
            return dict.TryGetValue(key, out var value) ? value : defaultValue;
        }

        #endregion
    }
}

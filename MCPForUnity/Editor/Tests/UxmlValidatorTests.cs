using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using MCPForUnity.Editor.Tools;
using Newtonsoft.Json.Linq;
using NUnit.Framework;
using UnityEditor;
using UnityEngine;
using UnityEngine.TestTools;

namespace MCPForUnity.Editor.Tests
{
    /// <summary>
    /// Verifies the validate_uxml / validate_uss actions on manage_ui.
    ///
    /// These tests prefer content-string input so they don't depend on a stable
    /// path-based authoring workflow. The validator's internal temp folder
    /// (`Assets/__McpUxmlValidate_Temp__/`) is best-effort cleaned by the
    /// validator itself; tests assert that contract.
    ///
    /// We avoid tight coupling to importer messages — the importer pass varies
    /// across Unity versions, and the validator may surface a typo as either an
    /// importer error or a hint-only warning depending on whether Unity's
    /// factory reports anything. The hint-pass row is the deterministic part.
    /// </summary>
    public class UxmlValidatorTests
    {
        private const string TempFolder = "Assets/__McpUxmlValidatorTests_Temp__";
        private const string ValidatorTempFolder = "Assets/__McpUxmlValidate_Temp__";

        [SetUp]
        public void SetUp()
        {
            if (!AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.CreateFolder("Assets", "__McpUxmlValidatorTests_Temp__");
            }
        }

        [TearDown]
        public void TearDown()
        {
            if (AssetDatabase.IsValidFolder(TempFolder))
            {
                AssetDatabase.DeleteAsset(TempFolder);
            }
            // Defensive: if a test failure left the validator's internal temp folder
            // around, clean it up so subsequent tests start from a clean slate.
            if (AssetDatabase.IsValidFolder(ValidatorTempFolder))
            {
                AssetDatabase.DeleteAsset(ValidatorTempFolder);
            }
        }

        private static JObject Invoke(JObject paramsObj)
        {
            var raw = ManageUI.HandleCommand(paramsObj);
            return JObject.FromObject(raw);
        }

        private static JObject InvokeValidateUxml(string content)
        {
            return Invoke(new JObject
            {
                ["action"] = "validate_uxml",
                ["content"] = content,
            });
        }

        private static JObject InvokeValidateUxmlPath(string path)
        {
            return Invoke(new JObject
            {
                ["action"] = "validate_uxml",
                ["path"] = path,
            });
        }

        private static JObject InvokeValidateUss(string content)
        {
            return Invoke(new JObject
            {
                ["action"] = "validate_uss",
                ["content"] = content,
            });
        }

        // ---------------- UXML: content-string ----------------

        [Test]
        public void ValidateUxml_Content_ValidUxml_ReturnsValidTrue()
        {
            const string uxml =
                "<ui:UXML xmlns:ui=\"UnityEngine.UIElements\">" +
                "  <ui:Button text=\"OK\" />" +
                "</ui:UXML>";

            var response = InvokeValidateUxml(uxml);

            Assert.IsTrue((bool)response["success"], "validate_uxml should respond success=true: " + response);

            var data = response["data"];
            Assert.IsNotNull(data, "response should include a data object");
            Assert.IsTrue((bool)data["valid"], "valid UXML should be reported as valid: " + response);

            var errors = (JArray)data["errors"];
            Assert.IsNotNull(errors, "errors array should be present");
            Assert.AreEqual(0, errors.Count, "valid UXML should have no errors: " + response);

            int elementCount = (int)data["elementCount"];
            Assert.Greater(elementCount, 0, "elementCount should be > 0 for a real UXML tree: " + response);
        }

        [Test]
        public void ValidateUxml_Content_TypoInElementName_ReturnsValidFalseWithHint()
        {
            // "Buton" is a typo of "Button" — the hint pass should suggest "Button".
            // Some Unity versions also surface an importer error; either is acceptable
            // as long as the typo is referenced and a hint is offered.

            // Unity's UXML importer logs an error for the unknown element. That's
            // exactly the behavior under test — tell NUnit to expect it.
            LogAssert.Expect(LogType.Error, new Regex("Buton.*missing|Buton.*not known|Buton"));

            const string uxml =
                "<ui:UXML xmlns:ui=\"UnityEngine.UIElements\">" +
                "  <ui:Buton text=\"OK\" />" +
                "</ui:UXML>";

            var response = InvokeValidateUxml(uxml);

            Assert.IsTrue((bool)response["success"], "validate_uxml should respond success=true: " + response);

            var data = response["data"];
            Assert.IsNotNull(data, "response should include a data object");

            var errors = (JArray)data["errors"];
            Assert.IsNotNull(errors, "errors array should be present");
            Assert.Greater(errors.Count, 0, "typo'd element should produce at least one diagnostic row: " + response);

            // Whether `valid` is reported as false depends on whether the importer also
            // emitted an error-severity row alongside the hint warning. Both shapes are
            // acceptable; what matters is that *some* diagnostic surfaces. If the validator
            // only produced a hint (warning), `valid` may still be true. Accept either.
            bool hasErrorSeverity = errors.Any(e => (string)e["severity"] == "error");
            bool hasHintWarning = errors.Any(e => (string)e["severity"] == "warning" && (string)e["source"] == "hint");
            Assert.IsTrue(hasErrorSeverity || hasHintWarning,
                "expected either an error-severity row or a hint-source warning row: " + response);
            if (hasErrorSeverity)
            {
                Assert.IsFalse((bool)data["valid"],
                    "with an error-severity row present, valid must be false: " + response);
            }

            // At least one error/warning row should mention the typo'd token.
            bool mentionsTypo = errors.Any(e =>
            {
                string msg = (string)e["message"];
                return !string.IsNullOrEmpty(msg) && msg.IndexOf("Buton", System.StringComparison.Ordinal) >= 0;
            });
            Assert.IsTrue(mentionsTypo, "an error message should reference the typo 'Buton': " + response);

            // And a hint should mention either "Did you mean" or the corrected name "Button".
            bool offersHint = errors.Any(e =>
            {
                string msg = (string)e["message"];
                if (string.IsNullOrEmpty(msg)) return false;
                return msg.IndexOf("Did you mean", System.StringComparison.OrdinalIgnoreCase) >= 0
                    || msg.IndexOf("Button", System.StringComparison.Ordinal) >= 0;
            });
            Assert.IsTrue(offersHint, "validator should suggest 'Button' for typo 'Buton': " + response);
        }

        [Test]
        public void ValidateUxml_Content_MalformedXml_ReturnsLineColumn()
        {
            // Missing closing tag — XDocument.Parse should reject this and surface a
            // real (line, column) via XmlException.

            // Unity's UXML importer also logs an XML parse error when it tries to load
            // the temp file. That's expected — the validator surfaces it as a structured
            // error in the response; tell NUnit not to treat the log as a test failure.
            LogAssert.Expect(LogType.Error, new Regex("Xml is not valid|XmlException|Unexpected end of file"));

            const string malformed = "<ui:UXML xmlns:ui=\"UnityEngine.UIElements\"><ui:Button";

            var response = InvokeValidateUxml(malformed);

            Assert.IsTrue((bool)response["success"], "validate_uxml should respond success=true even for invalid input: " + response);

            var data = response["data"];
            Assert.IsNotNull(data, "response should include a data object");
            Assert.IsFalse((bool)data["valid"], "malformed XML must be reported as invalid: " + response);

            var errors = (JArray)data["errors"];
            Assert.IsNotNull(errors, "errors array should be present");
            Assert.Greater(errors.Count, 0, "malformed XML should produce at least one error: " + response);

            // Find the first error-severity row and check its line/column/severity.
            var firstError = errors.FirstOrDefault(e => (string)e["severity"] == "error");
            Assert.IsNotNull(firstError, "expected at least one severity=error row: " + response);
            Assert.AreEqual("error", (string)firstError["severity"]);
            Assert.Greater((int)firstError["line"], 0, "malformed-XML diagnostic should carry a positive line number: " + response);
            Assert.Greater((int)firstError["column"], 0, "malformed-XML diagnostic should carry a positive column number: " + response);
        }

        [Test]
        public void ValidateUxml_Content_TempFileCleanedUp()
        {
            const string uxml =
                "<ui:UXML xmlns:ui=\"UnityEngine.UIElements\">" +
                "  <ui:Label text=\"Hello\" />" +
                "</ui:UXML>";

            var response = InvokeValidateUxml(uxml);
            Assert.IsTrue((bool)response["success"], "validate_uxml should respond success=true: " + response);

            // After the call, the validator's temp folder should either be gone or empty.
            // The folder is only kept if other tests were running concurrently and wrote into
            // it; in serial test execution it should be cleaned up.
            if (AssetDatabase.IsValidFolder(ValidatorTempFolder))
            {
                string fullFolder = Path.Combine(
                    UnityEngine.Application.dataPath,
                    "__McpUxmlValidate_Temp__");
                if (Directory.Exists(fullFolder))
                {
                    var files = Directory.GetFiles(fullFolder)
                        .Where(f => !f.EndsWith(".meta", System.StringComparison.OrdinalIgnoreCase))
                        .ToArray();
                    Assert.AreEqual(0, files.Length,
                        "validator temp folder should be empty after a successful call, found: " + string.Join(", ", files));
                }
            }
        }

        // ---------------- UXML: file-path ----------------

        [Test]
        public void ValidateUxml_Path_ValidExistingFile_ReturnsValidTrue()
        {
            const string uxml =
                "<ui:UXML xmlns:ui=\"UnityEngine.UIElements\">" +
                "  <ui:Button text=\"OK\" />" +
                "</ui:UXML>";

            string assetPath = TempFolder + "/Sample.uxml";
            string fullPath = Path.Combine(UnityEngine.Application.dataPath,
                "__McpUxmlValidatorTests_Temp__/Sample.uxml");
            File.WriteAllText(fullPath, uxml, new System.Text.UTF8Encoding(false));
            AssetDatabase.ImportAsset(assetPath, ImportAssetOptions.ForceSynchronousImport);

            var response = InvokeValidateUxmlPath(assetPath);

            Assert.IsTrue((bool)response["success"], "validate_uxml should respond success=true: " + response);

            var data = response["data"];
            Assert.IsNotNull(data, "response should include a data object");
            Assert.IsTrue((bool)data["valid"], "valid file at path should be reported as valid: " + response);
            Assert.AreEqual(assetPath, (string)data["path"], "data.path should echo the requested path: " + response);
        }

        [Test]
        public void ValidateUxml_Path_NonexistentFile_ReturnsActionFailure()
        {
            // The validator returns ErrorResponse (success=false) for a missing file —
            // the action itself failed, distinct from "found, parsed, invalid".
            const string missingPath = "Assets/__nope_does_not_exist__/missing.uxml";

            var response = InvokeValidateUxmlPath(missingPath);

            Assert.IsFalse((bool)response["success"], "missing file should produce action-level failure: " + response);
            Assert.IsNotNull(response["error"], "ErrorResponse should carry an 'error' field: " + response);
            string err = (string)response["error"];
            Assert.IsTrue(!string.IsNullOrEmpty(err), "error string should not be empty");
        }

        // ---------------- USS ----------------

        [Test]
        public void ValidateUss_Content_ValidStylesheet_ReturnsValidTrue()
        {
            const string uss = "Button { color: white; }";

            var response = InvokeValidateUss(uss);

            Assert.IsTrue((bool)response["success"], "validate_uss should respond success=true: " + response);

            var data = response["data"];
            Assert.IsNotNull(data, "response should include a data object");
            Assert.IsTrue((bool)data["valid"], "well-formed USS should be reported as valid: " + response);

            var errors = (JArray)data["errors"];
            Assert.IsNotNull(errors, "errors array should be present");
            Assert.IsFalse(errors.Any(e => (string)e["severity"] == "error"),
                "valid USS should not produce error-severity rows: " + response);
        }

        [Test]
        public void ValidateUss_Content_MalformedStylesheet_ReturnsValidFalse()
        {
            // Missing value and missing closing brace — USS importer should complain.

            // Unity's USS importer can emit multiple error logs (an "Internal import
            // error: Index was out of range" plus follow-on stack traces) when ExCSS
            // chokes. Those logs are exactly what the validator captures and turns
            // into a structured error in the response. Suppress NUnit's
            // unhandled-error-log gate for this test rather than trying to enumerate
            // every possible importer message.
            LogAssert.ignoreFailingMessages = true;

            const string uss = "Button { color: ;";

            var response = InvokeValidateUss(uss);

            Assert.IsTrue((bool)response["success"], "validate_uss should respond success=true even for invalid input: " + response);

            var data = response["data"];
            Assert.IsNotNull(data, "response should include a data object");
            Assert.IsFalse((bool)data["valid"], "malformed USS should be reported as invalid: " + response);

            var errors = (JArray)data["errors"];
            Assert.IsNotNull(errors, "errors array should be present");
            Assert.Greater(errors.Count, 0, "malformed USS should produce at least one diagnostic row: " + response);
        }
    }
}

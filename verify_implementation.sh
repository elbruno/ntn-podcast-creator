#!/bin/bash
echo "============================================================"
echo "Template Feature Implementation Verification"
echo "============================================================"
echo ""

# Check files exist
echo "✓ Checking files..."
files=(
    "features/template_manager.py"
    "tests/test_template_feature.py"
    "docs/TEMPLATE_FEATURE.md"
    "docs/TEMPLATE_FEATURE_UI.md"
    "docs/TEMPLATE_IMPLEMENTATION_SUMMARY.md"
)

all_exist=true
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file exists"
    else
        echo "  ✗ $file missing"
        all_exist=false
    fi
done

# Check templates directory
echo ""
echo "✓ Checking directories..."
if [ -d "core/templates" ]; then
    echo "  ✓ core/templates/ directory exists"
else
    echo "  ✗ core/templates/ directory missing"
    all_exist=false
fi

# Run tests
echo ""
echo "✓ Running tests..."
if python tests/test_template_feature.py > /tmp/test_output.txt 2>&1; then
    echo "  ✓ All tests passed"
    grep "ALL TESTS PASSED" /tmp/test_output.txt
else
    echo "  ✗ Tests failed"
    cat /tmp/test_output.txt
    all_exist=false
fi

# Check syntax
echo ""
echo "✓ Checking Python syntax..."
if python -m py_compile features/template_manager.py 2>/dev/null; then
    echo "  ✓ template_manager.py syntax valid"
else
    echo "  ✗ template_manager.py has syntax errors"
    all_exist=false
fi

if python -m py_compile features/config_manager.py 2>/dev/null; then
    echo "  ✓ config_manager.py syntax valid"
else
    echo "  ✗ config_manager.py has syntax errors"
    all_exist=false
fi

# Summary
echo ""
echo "============================================================"
if [ "$all_exist" = true ]; then
    echo "✅ VERIFICATION PASSED"
    echo "Template feature is fully implemented and ready!"
else
    echo "❌ VERIFICATION FAILED"
    echo "Some checks did not pass"
    exit 1
fi
echo "============================================================"

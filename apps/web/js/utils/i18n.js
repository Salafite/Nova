window.i18n = {
    dict: {
        'Products': 'المنتجات',
        'Sales': 'المبيعات',
        'Customers': 'العملاء',
        'Suppliers': 'الموردين',
        'Inventory': 'المخزون',
        'Warehouse': 'المستودع',
        'Finance': 'المالية',
        'Purchasing': 'المشتريات',
        'Manufacturing': 'التصنيع',
        'Planning': 'التخطيط',
        'Quality': 'الجودة',
        'Dashboard': 'لوحة القيادة',
        'Settings': 'الإعدادات',
        'POS': 'نقطة البيع',
        'Shop Floor': 'أرضية المصنع',
        'Admin': 'الإدارة',
        'Home': 'الرئيسية',
        'Name': 'الاسم',
        'Email': 'البريد الإلكتروني',
        'Role': 'الدور',
        'Status': 'الحالة',
        'Price': 'السعر',
        'Quantity': 'الكمية',
        'Total': 'الإجمالي',
        'Date': 'التاريخ',
        'Action': 'إجراء',
        'Add': 'إضافة',
        'Edit': 'تعديل',
        'Delete': 'حذف',
        'Save': 'حفظ',
        'Cancel': 'إلغاء',
        'Search': 'بحث',
        'View': 'عرض',
        'Close': 'إغلاق',
        'Category': 'الفئة',
        'SKU': 'رمز المنتج',
        'Cost': 'التكلفة',
        'Stock': 'المخزون',
        'Location': 'الموقع',
        'Notes': 'ملاحظات',
        'Phone': 'الهاتف',
        'Address': 'العنوان',
        'Company': 'الشركة',
        'Type': 'النوع',
        'Amount': 'المبلغ',
        'Reference': 'مرجع'
    },
    
    translate: function(element) {
        if (!element) return;
        const isAr = document.documentElement.lang === 'ar' || document.documentElement.dir === 'rtl';
        if (!isAr) return; // We assume the base HTML is in English

        // Walk through all text nodes inside the element
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null, false);
        let node;
        const nodesToReplace = [];

        while (node = walker.nextNode()) {
            if (node.parentElement && node.parentElement.tagName === 'SCRIPT') continue;
            const text = node.nodeValue.trim();
            if (text && this.dict[text]) {
                nodesToReplace.push({ node, original: text, translated: this.dict[text] });
            }
        }

        nodesToReplace.forEach(n => {
            n.node.nodeValue = n.node.nodeValue.replace(n.original, n.translated);
        });

        // Also translate placeholders for inputs
        const inputs = element.querySelectorAll('input[placeholder], textarea[placeholder]');
        inputs.forEach(input => {
            const placeholder = input.getAttribute('placeholder');
            if (placeholder && this.dict[placeholder]) {
                input.setAttribute('placeholder', this.dict[placeholder]);
            }
        });
    },
    
    observe: function() {
        if (this._observer) return;
        this._observer = new MutationObserver(mutations => {
            const isAr = document.documentElement.lang === 'ar' || document.documentElement.dir === 'rtl';
            if (!isAr) return;
            
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        window.i18n.translate(node);
                    } else if (node.nodeType === Node.TEXT_NODE) {
                        const text = node.nodeValue.trim();
                        if (text && window.i18n.dict[text]) {
                            node.nodeValue = node.nodeValue.replace(text, window.i18n.dict[text]);
                        }
                    }
                });
            });
        });
        
        const content = document.getElementById('content');
        if (content) {
            this._observer.observe(content, { childList: true, subtree: true });
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    window.i18n.observe();
});
if (document.getElementById('content')) {
    window.i18n.observe();
}

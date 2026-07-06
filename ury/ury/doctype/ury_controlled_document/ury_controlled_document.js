frappe.ui.form.on('URY Controlled Document', {
	refresh(frm) {
		if (frm.is_new()) return;

		if (frappe.user.has_role('System Manager') || frappe.user.has_role('URY Manager')) {
			frm.add_custom_button(__('Create New Revision'), () => {
				frappe.prompt(
					[{ fieldname: 'change_summary', fieldtype: 'Small Text', label: __('Change Summary') }],
					(values) => {
						frappe.call({
							method: 'ury.ury.doctype.ury_controlled_document.ury_controlled_document.create_new_revision',
							args: { document: frm.doc.name, change_summary: values.change_summary },
							callback: () => frm.reload_doc(),
						});
					},
					__('Create New Revision'),
					__('Create')
				);
			}, __('Document Control'));

			frm.add_custom_button(__('Publish'), () => {
				frappe.confirm(__('Publish this controlled document?'), () => {
					frappe.call({
						method: 'ury.ury.doctype.ury_controlled_document.ury_controlled_document.publish_document',
						args: { document: frm.doc.name },
						callback: () => frm.reload_doc(),
					});
				});
			}, __('Document Control'));

			frm.add_custom_button(__('Mark Superseded'), () => {
				frappe.prompt(
					[{ fieldname: 'superseded_by', fieldtype: 'Link', options: 'URY Controlled Document', label: __('Superseded By') }],
					(values) => {
						frappe.call({
							method: 'ury.ury.doctype.ury_controlled_document.ury_controlled_document.mark_superseded',
							args: { document: frm.doc.name, superseded_by: values.superseded_by },
							callback: () => frm.reload_doc(),
						});
					},
					__('Mark Superseded'),
					__('Update')
				);
			}, __('Document Control'));
		}

		if (frm.doc.status === 'Published') {
			frm.add_custom_button(__('Acknowledge'), () => {
				frappe.prompt(
					[{ fieldname: 'remarks', fieldtype: 'Small Text', label: __('Remarks') }],
					(values) => {
						frappe.call({
							method: 'ury.ury.doctype.ury_controlled_document.ury_controlled_document.acknowledge_document',
							args: { document: frm.doc.name, remarks: values.remarks },
							callback: (r) => frappe.msgprint(__('Acknowledgement recorded: {0}', [r.message])),
						});
					},
					__('Acknowledge Document'),
					__('Acknowledge')
				);
			}, __('Document Control'));
		}

		frm.add_custom_button(__('View Acknowledgements'), () => {
			frappe.set_route('List', 'URY Document Acknowledgement', { controlled_document: frm.doc.name });
		}, __('Document Control'));
	},
});

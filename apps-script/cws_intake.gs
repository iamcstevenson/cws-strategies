/**
 * CWS Strategies — Website Contact Form + Intake Automation  (v2, Oct 2026)
 *
 * The website (cherlynnstevenson.com) has its own on-brand contact form. Behind the
 * scenes it submits to the Google Form this script manages, so everything below
 * still runs on every submission.
 *
 * ONE-TIME UPGRADE FROM v1 (the long "New Website Project" questionnaire):
 *   1. Paste this whole file over the old code in the "CWS Intake" Apps Script project. Save.
 *   2. Choose "convertToContactForm" in the function dropdown and click Run.
 *   It rewrites the EXISTING form in place (same form, same trigger, same responses
 *   sheet), so nothing else needs reconnecting. Old responses stay in the sheet.
 *
 * ON EACH SUBMISSION (onIntakeSubmit):
 *   - Creates "Clients > <Organization> (YYYY-MM-DD)"
 *   - Saves an "00 Intake Answers — <Organization>" Google Doc in that folder
 *   - Emails you "[CWS Intake] <Organization>" with Reply-To set to the person who wrote in.
 *     The body keeps the "CLIENT_FOLDER_ID:" line the daily research task looks for.
 */

const CONFIG = {
  NOTIFY_EMAIL: 'crstevenson@gmail.com',
  FORM_ID: '1PrIn4W6V9gaVXf_VfboANiAx5K35rFqTsnJxs7jj0gA',     // the existing intake form
  CLIENTS_FOLDER_ID: '1IQRSt031JnhI3jmCYJIP1MKBP3SxFPdv',     // CWS Strategies > Clients
  FORM_FOLDER_ID: '1b8ki-zgn68pgjh1tFsfRnhGRYtZyX7bZ',        // CWS Strategies > Intake Form
  SUBJECT_PREFIX: '[CWS Intake]',
};

// Question titles. The website form, the notification email and the daily task rely on these.
const Q = {
  NAME: 'Your name',
  EMAIL: 'Email',
  ORG: 'Organization name',
  WEBSITE: 'Website',
  MESSAGE: 'What would you like to talk about?',
};

/** Run once to turn the old questionnaire into the short contact form. Safe to re-run. */
function convertToContactForm() {
  const form = FormApp.openById(CONFIG.FORM_ID);

  form.getItems().forEach(function (item) { form.deleteItem(item); });

  form
    .setTitle('CWS Strategies — Contact')
    .setDescription('Tell us who you are and what you would like to talk about.')
    .setConfirmationMessage("Thanks! We've got your message and will be in touch soon.")
    .setProgressBar(false)
    .setCollectEmail(false)
    .setAllowResponseEdits(false)
    .setLimitOneResponsePerUser(false);
  try { form.setRequireLogin(false); } catch (err) { /* only applies to Workspace accounts */ }

  form.addTextItem().setTitle(Q.NAME).setRequired(true);
  form.addTextItem().setTitle(Q.EMAIL).setRequired(true)
    .setValidation(FormApp.createTextValidation().requireTextIsEmail().build());
  form.addTextItem().setTitle(Q.ORG).setRequired(true);
  form.addTextItem().setTitle(Q.WEBSITE);
  form.addParagraphTextItem().setTitle(Q.MESSAGE).setRequired(true);

  // Make sure exactly one submit trigger points at onIntakeSubmit.
  const existing = ScriptApp.getProjectTriggers().filter(function (t) {
    return t.getHandlerFunction() === 'onIntakeSubmit';
  });
  if (existing.length === 0) {
    ScriptApp.newTrigger('onIntakeSubmit').forForm(form).onFormSubmit().create();
  } else {
    existing.slice(1).forEach(function (t) { ScriptApp.deleteTrigger(t); });
  }

  Logger.log('Form updated. Public link: ' + form.getPublishedUrl());
  Logger.log('Edit link: ' + form.getEditUrl());
}

function onIntakeSubmit(e) {
  const answers = e.response.getItemResponses().map(function (r) {
    return { q: r.getItem().getTitle(), a: formatAnswer_(r.getResponse()) };
  });
  const get = function (title) {
    const hit = answers.find(function (x) { return x.q === title; });
    return hit ? hit.a.trim() : '';
  };

  const name = get(Q.NAME);
  const email = get(Q.EMAIL);
  const org = get(Q.ORG) || name || 'Unnamed contact';
  const stamp = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');

  // Client folder
  const clientFolder = DriveApp.getFolderById(CONFIG.CLIENTS_FOLDER_ID)
    .createFolder(org + ' (' + stamp + ')');

  // Intake answers doc
  const doc = DocumentApp.create('00 Intake Answers — ' + org);
  const body = doc.getBody();
  body.appendParagraph('Contact request: ' + org).setHeading(DocumentApp.ParagraphHeading.HEADING1);
  body.appendParagraph('Submitted ' + stamp + ' via the website contact form');
  answers.forEach(function (x) {
    body.appendParagraph(x.q).setHeading(DocumentApp.ParagraphHeading.HEADING3);
    body.appendParagraph(x.a || '—');
  });
  doc.saveAndClose();
  DriveApp.getFileById(doc.getId()).moveTo(clientFolder);

  // Notification email. The daily research task looks for this subject and the CLIENT_FOLDER_ID line.
  const text = answers.map(function (x) { return x.q + ':\n' + (x.a || '—'); }).join('\n\n');
  const mail = {
    to: CONFIG.NOTIFY_EMAIL,
    subject: CONFIG.SUBJECT_PREFIX + ' ' + org,
    body:
      'New contact request from the website.\n\n' +
      'CLIENT_FOLDER_ID: ' + clientFolder.getId() + '\n' +
      'Client folder: ' + clientFolder.getUrl() + '\n\n' +
      '---------------------------------\n\n' +
      text + '\n\n' +
      '(Reply to this email to answer ' + (name || 'them') + ' directly.)',
  };
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) mail.replyTo = email;
  MailApp.sendEmail(mail);
}

function formatAnswer_(value) {
  if (Array.isArray(value)) return value.join(', ');
  return value == null ? '' : String(value);
}

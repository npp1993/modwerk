// SPDX-License-Identifier: Elastic-2.0
// Copyright (c) 2026 Jannik Aßfalg (repeat98)
import campaign from './module-update-catchup-content.json'
import type { NotificationItem } from '../src/community/notification-contract'
import { notificationLines } from '../src/community/notification-text'
import { escape } from './account-email-template'
import { renderNewsEmail } from './news-email-template'

/** Operator-only recovery uses the ordinary notification queue, preferences and unsubscribe token. */
export const MODULE_UPDATE_CATCHUP = 'module-update-catchup-2026-10-20'

export function renderModuleUpdateCatchup(items: NotificationItem[], urls: { app: string; settings: string; unsubscribe: string }) {
  const app = new URL(urls.app)
  const modules = items.map(item => ({
    name: item.title ?? item.module_id ?? 'Module', version: item.module_version ?? '',
    href: notificationLines([item], target => new URL(target, app).href)[0].href,
  }))
  const message = renderNewsEmail({ ...campaign, body: campaign.body.replace('{{followed_updates}}', 'FOLLOWEDMODULEUPDATES') }, urls)
  const cells = modules.map(module => `<td width="50%" valign="top" style="width:50%;padding:9px 12px 9px 0;"><a href="${escape(module.href)}" style="color:#f4f4f8;font-size:14px;line-height:20px;text-decoration:none;font-weight:bold;">${escape(module.name)}</a><br><span style="color:#92929f;font-size:11px;line-height:17px;">${escape(module.version)}</span></td>`)
  const rows: string[] = []
  for (let index = 0; index < cells.length; index += 2) rows.push('<tr>' + cells[index] + (cells[index + 1] ?? '<td width="50%"></td>') + '</tr>')
  const panel = `<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="#1c1c1f" style="margin:4px 0 24px;border:1px solid #36363e;border-left:3px solid #c7a16c;border-radius:7px;"><tr><td style="padding:17px 18px 10px;"><p style="margin:0 0 5px;color:#c7a16c;font-size:12px;line-height:19px;font-weight:bold;">Updates for modules you follow</p><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">${rows.join('')}</table></td></tr></table>`
  const image = `<table role="presentation" width="100%" style="margin:4px 0 22px;"><tr><td><img src="${escape(new URL(campaign.image, app).href)}" alt="Octatrack beta status showing CPU and both DSP load meters, module sets and recent history" width="502" style="display:block;width:100%;height:auto;border:1px solid #36363e;border-radius:8px;"><p style="margin:7px 0 0;color:#90909e;font-size:11px;line-height:17px;">A look inside the Octatrack beta. Module availability varies.</p></td></tr></table>`
  message.html = message.html.replace(/<p[^>]*>FOLLOWEDMODULEUPDATES<\/p>/, panel)
    .replace('>Modwerk news<', '>A note from Jannik<')
    .replace(/(<p[^>]*>I’m spending a lot)/, image + '$1')
    .replace(/<p style="margin:0 0 18px;color:#c4c4ce;font-size:15px;line-height:25px;"><a href="https:\/\/modwerk.app\/"[^>]*>([^<]+)<\/a><\/p>/, '<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 24px;"><tr><td bgcolor="#c7a16c" style="border-radius:6px;"><a href="https://modwerk.app/" style="display:inline-block;padding:14px 20px;color:#171719;text-decoration:none;font-weight:bold;font-size:15px;">$1</a></td></tr></table>')
  message.text = message.text.replace('FOLLOWEDMODULEUPDATES', 'Updates for modules you follow:\n' + modules.map(module => module.name + ' ' + module.version + '\n' + module.href).join('\n'))
  return message
}

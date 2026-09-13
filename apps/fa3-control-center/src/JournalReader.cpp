#include "JournalReader.h"

#include <QDateTime>
#include <QVariantMap>
#include <systemd/sd-journal.h>

namespace {
QString field(sd_journal *journal, const char *name)
{
    const void *data=nullptr; size_t length=0;
    if(sd_journal_get_data(journal,name,&data,&length)<0||!data) return {};
    const QByteArray raw(static_cast<const char*>(data),qsizetype(length));
    const int eq=raw.indexOf('=');
    return QString::fromUtf8(eq>=0?raw.mid(eq+1):raw);
}
}

JournalReader::JournalReader(QObject *parent):QObject(parent)
{
    refresh();
}

void JournalReader::refresh(int maxEntries)
{
    m_entries.clear();
    sd_journal *journal=nullptr;
    const int openResult=sd_journal_open(&journal,SD_JOURNAL_LOCAL_ONLY);
    if(openResult<0||!journal){m_statusText=QStringLiteral("journald unavailable or not readable");emit entriesChanged();return;}
    sd_journal_seek_tail(journal);
    const int limit=qBound(25,maxEntries,1000);
    for(int i=0;i<limit && sd_journal_previous(journal)>0;++i){
        uint64_t usec=0; sd_journal_get_realtime_usec(journal,&usec);
        QVariantMap row;
        row.insert("timestamp",QDateTime::fromMSecsSinceEpoch(qint64(usec/1000)).toString(Qt::ISODate));
        row.insert("unit",field(journal,"_SYSTEMD_UNIT"));
        row.insert("identifier",field(journal,"SYSLOG_IDENTIFIER"));
        row.insert("priority",field(journal,"PRIORITY"));
        row.insert("message",field(journal,"MESSAGE"));
        if(!row.value("message").toString().isEmpty()) m_entries.append(row);
    }
    sd_journal_close(journal);
    m_statusText=QStringLiteral("read-only journald projection · %1 entries").arg(m_entries.size());
    emit entriesChanged();
}

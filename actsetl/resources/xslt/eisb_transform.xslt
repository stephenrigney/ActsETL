<xsl:stylesheet version="1.0"
        xmlns:xsl="http://www.w3.org/1999/XSL/Transform">    

    <xsl:template match="odq">“</xsl:template>
    <xsl:template match="cdq">”</xsl:template>
    <xsl:template match="osq">‘</xsl:template>
    <xsl:template match="csq">’</xsl:template>
    <xsl:template match="emdash">—</xsl:template>
    <xsl:template match="afada">á</xsl:template>
    <xsl:template match="Afada">Á</xsl:template>
    <xsl:template match="efada">é</xsl:template>
    <xsl:template match="Efada">É</xsl:template>
    <xsl:template match="ifada">í</xsl:template>
    <xsl:template match="Ifada">Í</xsl:template>
    <xsl:template match="ofada">ó</xsl:template>
    <xsl:template match="Ofada">Ó</xsl:template>
    <xsl:template match="ufada">ú</xsl:template>
    <xsl:template match="Ufada">Ú</xsl:template>
    <xsl:template match="euro">€</xsl:template>
    <xsl:template match="pound">£</xsl:template>
    <xsl:template match="euro">€</xsl:template>
    <xsl:template match="bull">•</xsl:template>
    <xsl:template match="nbsp">&#160;</xsl:template>  
    <xsl:template match="degree">°</xsl:template>
    <xsl:template match="dagger">†</xsl:template>
    <xsl:template match="ddagger">††</xsl:template>
    <!--
        The attribute is <unicode ch="E008"/>
        <xsl:template match="unicode">è</xsl:template>
    -->




    <!-- How to copy XML without changes
         http://mrhaki.blogspot.com/2008/07/copy-xml-as-is-with-xslt.html -->    
    <xsl:template match="*">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>
    <xsl:template match="@*|text()|comment()|processing-instruction">
        <xsl:copy-of select="."/>
    </xsl:template>
    </xsl:stylesheet>
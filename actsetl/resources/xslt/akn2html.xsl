<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
                xmlns:an="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">   
    <xsl:output method="html" encoding="UTF-8" indent="no" />
    <xsl:template match="an:akomaNtoso/an:bill/an:body">
        <html>
            <body>
                <xsl:for-each select="an:section">
                    <div class="section">
                        <h2 class="sectionheading"><xsl:value-of select="an:heading"/></h2>
                        <div class="sectionFirstPara">
                            <p><span class="sectionNum"><b><xsl:value-of select="an:num"/> </b></span> 
                                <xsl:choose>
                                    <xsl:when test="(./an:intro or ./an:content)">
                                        <span class="introText"><xsl:value-of select=".//an:p[1]"/></span>
                                    </xsl:when>
                                    
                                    <xsl:otherwise>
                                        <span class="introNum"><xsl:value-of select="*/an:num"/> </span>
                                        <span class="introText"><xsl:value-of select="*/*/an:p"/></span>
                                    </xsl:otherwise>
                                </xsl:choose>
                                </p>
                        </div>
                                
                        <xsl:for-each select="./an:subsection[position()>1]">
                            <div class="subsection">
                                <div class="sectionFirstPara">
                                    <p><span class="subsectionNum"><xsl:value-of select="an:num"/> </span> 
                                            <xsl:choose>
                                                <xsl:when test="(./an:intro or ./an:content)">
                                                    <span class="introText"><xsl:value-of select=".//an:p"/></span>
                                                </xsl:when>
                                                <xsl:otherwise>
                                                    <span class="introNum"><xsl:value-of select="*/an:num"/> </span>
                                                    <span class="introText"><xsl:value-of select="*/*/an:p"/></span>
                                                </xsl:otherwise>
                                            </xsl:choose>
                                    </p>
                                </div>
                            </div>    
                        </xsl:for-each>

                        <xsl:for-each select="./an:paragraph">
                            <div class="paragraph">
                                <div class="paragraphFirstPara">
                                    <p><span class="paragraphNum"><xsl:value-of select="an:num"/> </span> 
                                            <xsl:choose>
                                                <xsl:when test="(./an:intro or ./an:content)">
                                                    <span class="introText"><xsl:value-of select=".//an:p"/></span>
                                                </xsl:when>
                                                <xsl:otherwise>
                                                    <span class="introNum"><xsl:value-of select="*/an:num"/> </span>
                                                    <span class="introText"><xsl:value-of select="*/*/an:p"/></span>
                                                </xsl:otherwise>
                                            </xsl:choose>
                                    </p>
                                </div>
                            </div>    
                        </xsl:for-each>

                            </div>
                        </xsl:for-each>
                        
                    </body>
                    
                </html>
            </xsl:template>
        </xsl:stylesheet>
        